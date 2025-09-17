from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
import hashlib
import logging
from datetime import datetime
from db.database import engine
from db.models import Game, GameRule

rules_bp = Blueprint('rules', __name__)
Session = sessionmaker(bind=engine)

def hash_admin_code(admin_code: str) -> str:
    """Hash an admin code for audit logging"""
    return hashlib.sha256(admin_code.encode()).hexdigest()

def require_admin_access(public_code: str, admin_code: str) -> Game:
    """Validate admin access and return the game"""
    with Session() as session:
        game = session.query(Game).filter_by(public_code=public_code.upper()).first()
        if not game:
            raise ValueError("Game not found")

        if game.admin_code != admin_code:
            raise ValueError("Invalid admin code")

        return game

@rules_bp.route('/games/<public_code>/rules', methods=['GET'])
def get_game_rules(public_code):
    """Get all rules for a game"""
    try:
        with Session() as session:
            game = session.query(Game).filter_by(public_code=public_code.upper()).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404

            rules = session.query(GameRule)\
                .filter_by(game_id=game.id)\
                .order_by(GameRule.order_index, GameRule.created_at)\
                .all()

            rules_data = []
            for rule in rules:
                rules_data.append({
                    "id": str(rule.id),
                    "title": rule.title,
                    "content": rule.content,
                    "order_index": rule.order_index,
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": rule.updated_at.isoformat()
                })

            return jsonify({
                "success": True,
                "rules": rules_data
            })

    except Exception as e:
        logging.error(f"Error fetching rules for game {public_code}: {str(e)}")
        return jsonify({"error": "Failed to fetch rules"}), 500

@rules_bp.route('/games/<public_code>/rules', methods=['POST'])
def create_rule(public_code):
    """Create a new rule (admin only)"""
    try:
        admin_code = request.headers.get('X-Admin-Code')
        if not admin_code:
            return jsonify({"error": "Admin access required"}), 401

        data = request.json
        if not data or not data.get('title') or not data.get('content'):
            return jsonify({"error": "Title and content are required"}), 400

        # Validate admin access
        game = require_admin_access(public_code, admin_code)
        admin_hash = hash_admin_code(admin_code)

        with Session() as session:
            # Get the highest order_index for this game
            max_order = session.query(GameRule.order_index)\
                .filter_by(game_id=game.id)\
                .order_by(GameRule.order_index.desc())\
                .first()

            next_order = (max_order[0] + 1) if max_order and max_order[0] is not None else 0

            # Create new rule
            new_rule = GameRule(
                game_id=game.id,
                title=data['title'].strip(),
                content=data['content'].strip(),
                order_index=data.get('order_index', next_order),
                created_by=admin_hash
            )

            session.add(new_rule)
            session.commit()

            return jsonify({
                "success": True,
                "rule": {
                    "id": str(new_rule.id),
                    "title": new_rule.title,
                    "content": new_rule.content,
                    "order_index": new_rule.order_index,
                    "created_at": new_rule.created_at.isoformat(),
                    "updated_at": new_rule.updated_at.isoformat()
                }
            }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logging.error(f"Error creating rule for game {public_code}: {str(e)}")
        return jsonify({"error": "Failed to create rule"}), 500

@rules_bp.route('/games/<public_code>/rules/<rule_id>', methods=['PUT'])
def update_rule(public_code, rule_id):
    """Update an existing rule (admin only)"""
    try:
        admin_code = request.headers.get('X-Admin-Code')
        if not admin_code:
            return jsonify({"error": "Admin access required"}), 401

        data = request.json
        if not data:
            return jsonify({"error": "Request data required"}), 400

        # Validate admin access
        game = require_admin_access(public_code, admin_code)

        with Session() as session:
            rule = session.query(GameRule)\
                .filter_by(id=rule_id, game_id=game.id)\
                .first()

            if not rule:
                return jsonify({"error": "Rule not found"}), 404

            # Update fields if provided
            if 'title' in data:
                rule.title = data['title'].strip()
            if 'content' in data:
                rule.content = data['content'].strip()
            if 'order_index' in data:
                rule.order_index = data['order_index']

            session.commit()

            return jsonify({
                "success": True,
                "rule": {
                    "id": str(rule.id),
                    "title": rule.title,
                    "content": rule.content,
                    "order_index": rule.order_index,
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": rule.updated_at.isoformat()
                }
            })

    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logging.error(f"Error updating rule {rule_id} for game {public_code}: {str(e)}")
        return jsonify({"error": "Failed to update rule"}), 500

@rules_bp.route('/games/<public_code>/rules/<rule_id>', methods=['DELETE'])
def delete_rule(public_code, rule_id):
    """Delete a rule (admin only)"""
    try:
        admin_code = request.headers.get('X-Admin-Code')
        if not admin_code:
            return jsonify({"error": "Admin access required"}), 401

        # Validate admin access
        game = require_admin_access(public_code, admin_code)

        with Session() as session:
            rule = session.query(GameRule)\
                .filter_by(id=rule_id, game_id=game.id)\
                .first()

            if not rule:
                return jsonify({"error": "Rule not found"}), 404

            session.delete(rule)
            session.commit()

            return jsonify({"success": True, "message": "Rule deleted"})

    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logging.error(f"Error deleting rule {rule_id} for game {public_code}: {str(e)}")
        return jsonify({"error": "Failed to delete rule"}), 500

@rules_bp.route('/games/<public_code>/rules/reorder', methods=['PUT'])
def reorder_rules(public_code):
    """Reorder rules (admin only)"""
    try:
        admin_code = request.headers.get('X-Admin-Code')
        if not admin_code:
            return jsonify({"error": "Admin access required"}), 401

        data = request.json
        if not data or 'rule_orders' not in data:
            return jsonify({"error": "rule_orders array required"}), 400

        # Validate admin access
        game = require_admin_access(public_code, admin_code)

        with Session() as session:
            # Update order_index for each rule
            for item in data['rule_orders']:
                rule_id = item.get('id')
                new_order = item.get('order_index')

                if rule_id is not None and new_order is not None:
                    rule = session.query(GameRule)\
                        .filter_by(id=rule_id, game_id=game.id)\
                        .first()

                    if rule:
                        rule.order_index = new_order

            session.commit()

            return jsonify({"success": True, "message": "Rules reordered"})

    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logging.error(f"Error reordering rules for game {public_code}: {str(e)}")
        return jsonify({"error": "Failed to reorder rules"}), 500