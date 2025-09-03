# services/ledger_analysis_service.py
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Game, Session as SessionModel, SessionPlayerSummary, Player

log = logging.getLogger(__name__)


def get_ledger_analysis(public_code: str) -> Dict[str, Any]:
    """
    Analyze ledger balance and identify discrepancies for a specific game.
    Returns comprehensive analysis of buy-ins vs cash-outs.
    """
    with SessionLocal() as db:
        # Get the game
        game = db.execute(select(Game).where(Game.public_code == public_code)).scalar_one_or_none()
        if not game:
            raise ValueError(f"Game with code {public_code} not found")
        
        # Overall balance analysis
        overall_stats = _get_overall_balance(db, game.id)
        
        # Session-by-session analysis
        session_analysis = _get_session_analysis(db, game.id)
        
        # Player anomaly analysis
        player_anomalies = _get_player_anomalies(db, game.id)
        
        # Problem identification
        problems = _identify_problems(db, game.id)
        
        # Temporal consistency checks
        temporal_issues = _check_temporal_consistency(db, game.id)
        
        # Statistical outlier detection
        statistical_outliers = _detect_statistical_outliers(db, game.id)
        
        # Cross-session validation
        cross_session_issues = _validate_cross_session_data(db, game.id)
        
        # Business logic violations
        business_logic_violations = _check_business_logic_violations(db, game.id)
        
        return {
            "game_code": public_code,
            "overall_balance": overall_stats,
            "session_analysis": session_analysis,
            "player_anomalies": player_anomalies,
            "problems": problems,
            "temporal_issues": temporal_issues,
            "statistical_outliers": statistical_outliers,
            "cross_session_issues": cross_session_issues,
            "business_logic_violations": business_logic_violations
        }


def _get_overall_balance(db: Session, game_id: str) -> Dict[str, Any]:
    """Calculate overall balance statistics for the game."""
    result = db.execute(text("""
        SELECT 
            COALESCE(SUM(sps.buy_in_sum), 0) as total_buy_ins,
            COALESCE(SUM(sps.cash_out_sum), 0) as total_cash_outs,
            COALESCE(SUM(sps.in_game), 0) as total_in_game,
            COALESCE(SUM(sps.net), 0) as total_net,
            COUNT(DISTINCT s.id) as total_sessions,
            COUNT(*) as total_entries
        FROM sessions s
        JOIN session_player_summaries sps ON s.id = sps.session_id
        WHERE s.game_id = :game_id
    """), {"game_id": game_id}).fetchone()
    
    if not result:
        return {
            "total_buy_ins": 0,
            "total_cash_outs": 0,
            "total_in_game": 0,
            "total_net": 0,
            "effective_cash_outs": 0,
            "balance": 0,
            "is_balanced": True,
            "imbalance_percentage": 0.0,
            "total_sessions": 0,
            "total_entries": 0
        }
    
    total_buy_ins = int(result.total_buy_ins or 0)
    total_cash_outs = int(result.total_cash_outs or 0)
    total_in_game = int(result.total_in_game or 0)
    total_net = int(result.total_net or 0)
    
    # Effective cash outs include money still in game
    effective_cash_outs = total_cash_outs + total_in_game
    balance = effective_cash_outs - total_buy_ins
    is_balanced = balance == 0
    
    imbalance_percentage = 0.0
    if total_buy_ins > 0:
        imbalance_percentage = (abs(balance) / total_buy_ins) * 100
    
    return {
        "total_buy_ins": total_buy_ins,
        "total_cash_outs": total_cash_outs,
        "total_in_game": total_in_game,
        "total_net": total_net,
        "effective_cash_outs": effective_cash_outs,
        "balance": balance,
        "is_balanced": is_balanced,
        "imbalance_percentage": round(imbalance_percentage, 2),
        "total_sessions": int(result.total_sessions or 0),
        "total_entries": int(result.total_entries or 0)
    }


def _get_session_analysis(db: Session, game_id: str) -> List[Dict[str, Any]]:
    """Analyze balance for each session."""
    results = db.execute(text("""
        SELECT 
            s.id as session_id,
            s.external_id,
            s.game_number,
            s.started_at,
            COALESCE(SUM(sps.buy_in_sum), 0) as session_buy_ins,
            COALESCE(SUM(sps.cash_out_sum), 0) as session_cash_outs,
            COALESCE(SUM(sps.in_game), 0) as session_in_game,
            COALESCE(SUM(sps.net), 0) as session_net,
            COUNT(sps.player_id) as player_count
        FROM sessions s
        LEFT JOIN session_player_summaries sps ON s.id = sps.session_id
        WHERE s.game_id = :game_id
        GROUP BY s.id, s.external_id, s.game_number, s.started_at
        ORDER BY s.game_number DESC, s.started_at DESC
    """), {"game_id": game_id}).fetchall()
    
    sessions = []
    for row in results:
        buy_ins = int(row.session_buy_ins or 0)
        cash_outs = int(row.session_cash_outs or 0)
        in_game = int(row.session_in_game or 0)
        effective_cash_outs = cash_outs + in_game
        balance = effective_cash_outs - buy_ins
        
        sessions.append({
            "session_id": str(row.session_id),
            "external_id": row.external_id,
            "game_number": row.game_number,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "buy_ins": buy_ins,
            "cash_outs": cash_outs,
            "in_game": in_game,
            "effective_cash_outs": effective_cash_outs,
            "balance": balance,
            "is_balanced": balance == 0,
            "player_count": int(row.player_count or 0),
            "has_significant_in_game": in_game > (buy_ins * 0.1) if buy_ins > 0 else in_game > 0
        })
    
    return sessions


def _get_player_anomalies(db: Session, game_id: str) -> List[Dict[str, Any]]:
    """Identify players with unusual patterns."""
    results = db.execute(text("""
        SELECT 
            p.id as player_id,
            p.display_name,
            p.external_id,
            COUNT(sps.session_id) as session_count,
            COALESCE(SUM(sps.buy_in_sum), 0) as total_buy_ins,
            COALESCE(SUM(sps.cash_out_sum), 0) as total_cash_outs,
            COALESCE(SUM(sps.in_game), 0) as total_in_game,
            COALESCE(SUM(sps.net), 0) as total_net,
            COUNT(CASE WHEN sps.buy_in_sum = 0 THEN 1 END) as zero_buy_in_count,
            COUNT(CASE WHEN sps.cash_out_sum = 0 AND sps.in_game = 0 THEN 1 END) as zero_cash_out_count
        FROM players p
        JOIN session_player_summaries sps ON p.id = sps.player_id
        JOIN sessions s ON sps.session_id = s.id
        WHERE s.game_id = :game_id
        GROUP BY p.id, p.display_name, p.external_id
        ORDER BY p.display_name
    """), {"game_id": game_id}).fetchall()
    
    anomalies = []
    for row in results:
        buy_ins = int(row.total_buy_ins or 0)
        cash_outs = int(row.total_cash_outs or 0)
        in_game = int(row.total_in_game or 0)
        session_count = int(row.session_count or 0)
        zero_buy_ins = int(row.zero_buy_in_count or 0)
        zero_cash_outs = int(row.zero_cash_out_count or 0)
        
        issues = []
        
        # Identify potential issues
        if zero_buy_ins > 0:
            issues.append(f"{zero_buy_ins} sessions with zero buy-ins")
        if zero_cash_outs > 0:
            issues.append(f"{zero_cash_outs} sessions with zero cash-outs")
        if buy_ins == 0 and cash_outs > 0:
            issues.append("Cash-out without buy-in")
        if cash_outs == 0 and in_game == 0 and buy_ins > 0:
            issues.append("Buy-in without cash-out or in-game amount")
        
        if issues:  # Only include players with potential issues
            anomalies.append({
                "player_id": str(row.player_id),
                "display_name": row.display_name,
                "external_id": row.external_id,
                "session_count": session_count,
                "total_buy_ins": buy_ins,
                "total_cash_outs": cash_outs,
                "total_in_game": in_game,
                "total_net": int(row.total_net or 0),
                "issues": issues
            })
    
    return anomalies


def _identify_problems(db: Session, game_id: str) -> Dict[str, Any]:
    """Identify specific problems that could cause imbalances."""
    problems = {
        "unbalanced_sessions": [],
        "missing_data_sessions": [],
        "high_in_game_sessions": [],
        "duplicate_concerns": []
    }
    
    # Find unbalanced sessions
    unbalanced = db.execute(text("""
        SELECT 
            s.id as session_id,
            s.external_id,
            s.game_number,
            (COALESCE(SUM(sps.cash_out_sum), 0) + COALESCE(SUM(sps.in_game), 0)) - COALESCE(SUM(sps.buy_in_sum), 0) as balance
        FROM sessions s
        LEFT JOIN session_player_summaries sps ON s.id = sps.session_id
        WHERE s.game_id = :game_id
        GROUP BY s.id, s.external_id, s.game_number
        HAVING (COALESCE(SUM(sps.cash_out_sum), 0) + COALESCE(SUM(sps.in_game), 0)) - COALESCE(SUM(sps.buy_in_sum), 0) != 0
        ORDER BY ABS((COALESCE(SUM(sps.cash_out_sum), 0) + COALESCE(SUM(sps.in_game), 0)) - COALESCE(SUM(sps.buy_in_sum), 0)) DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in unbalanced:
        problems["unbalanced_sessions"].append({
            "session_id": str(row.session_id),
            "external_id": row.external_id,
            "game_number": row.game_number,
            "balance": int(row.balance)
        })
    
    # Find sessions with no player data
    missing_data = db.execute(text("""
        SELECT s.id as session_id, s.external_id, s.game_number
        FROM sessions s
        LEFT JOIN session_player_summaries sps ON s.id = sps.session_id
        WHERE s.game_id = :game_id AND sps.session_id IS NULL
        ORDER BY s.game_number DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in missing_data:
        problems["missing_data_sessions"].append({
            "session_id": str(row.session_id),
            "external_id": row.external_id,
            "game_number": row.game_number
        })
    
    # Find sessions with high in_game amounts (potential incomplete sessions)
    high_in_game = db.execute(text("""
        SELECT 
            s.id as session_id,
            s.external_id,
            s.game_number,
            COALESCE(SUM(sps.in_game), 0) as total_in_game,
            COALESCE(SUM(sps.buy_in_sum), 0) as total_buy_ins
        FROM sessions s
        JOIN session_player_summaries sps ON s.id = sps.session_id
        WHERE s.game_id = :game_id
        GROUP BY s.id, s.external_id, s.game_number
        HAVING COALESCE(SUM(sps.in_game), 0) > COALESCE(SUM(sps.buy_in_sum), 0) * 0.15
        ORDER BY total_in_game DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in high_in_game:
        problems["high_in_game_sessions"].append({
            "session_id": str(row.session_id),
            "external_id": row.external_id,
            "game_number": row.game_number,
            "total_in_game": int(row.total_in_game),
            "total_buy_ins": int(row.total_buy_ins),
            "percentage": round((int(row.total_in_game) / max(int(row.total_buy_ins), 1)) * 100, 1)
        })
    
    return problems


def _check_temporal_consistency(db: Session, game_id: str) -> Dict[str, Any]:
    """Check for temporal consistency issues."""
    issues = {
        "future_dates": [],
        "game_number_gaps": [],
        "duplicate_game_numbers": [],
        "chronological_violations": []
    }
    
    # Find sessions with future dates
    future_dates = db.execute(text("""
        SELECT s.id, s.external_id, s.game_number, s.started_at
        FROM sessions s
        WHERE s.game_id = :game_id 
        AND s.started_at > NOW()
        ORDER BY s.started_at DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in future_dates:
        issues["future_dates"].append({
            "session_id": str(row.id),
            "external_id": row.external_id,
            "game_number": row.game_number,
            "started_at": row.started_at.isoformat() if row.started_at else None
        })
    
    # Find game number gaps and duplicates
    game_numbers = db.execute(text("""
        SELECT game_number, COUNT(*) as count, 
               array_agg(s.external_id ORDER BY s.started_at) as external_ids,
               array_agg(s.id::text ORDER BY s.started_at) as session_ids
        FROM sessions s
        WHERE s.game_id = :game_id AND s.game_number IS NOT NULL
        GROUP BY game_number
        ORDER BY game_number
    """), {"game_id": game_id}).fetchall()
    
    if game_numbers:
        # Check for duplicates
        for row in game_numbers:
            if row.count > 1:
                issues["duplicate_game_numbers"].append({
                    "game_number": row.game_number,
                    "count": row.count,
                    "external_ids": row.external_ids,
                    "session_ids": row.session_ids
                })
        
        # Check for gaps in sequence
        expected_numbers = set(range(1, max(row.game_number for row in game_numbers) + 1))
        actual_numbers = set(row.game_number for row in game_numbers)
        missing_numbers = sorted(expected_numbers - actual_numbers)
        
        if missing_numbers:
            issues["game_number_gaps"] = missing_numbers
    
    # Check chronological order violations (game number vs date order)
    chronological = db.execute(text("""
        SELECT s1.game_number as game1, s1.started_at as date1, s1.external_id as ext1,
               s2.game_number as game2, s2.started_at as date2, s2.external_id as ext2
        FROM sessions s1, sessions s2
        WHERE s1.game_id = :game_id AND s2.game_id = :game_id
        AND s1.game_number < s2.game_number
        AND s1.started_at > s2.started_at
        AND s1.started_at IS NOT NULL AND s2.started_at IS NOT NULL
        ORDER BY s1.game_number
    """), {"game_id": game_id}).fetchall()
    
    for row in chronological:
        issues["chronological_violations"].append({
            "earlier_game": {"number": row.game1, "date": row.date1.isoformat(), "external_id": row.ext1},
            "later_game": {"number": row.game2, "date": row.date2.isoformat(), "external_id": row.ext2}
        })
    
    return issues


def _detect_statistical_outliers(db: Session, game_id: str) -> Dict[str, Any]:
    """Detect statistical outliers in monetary amounts."""
    outliers = {
        "unusual_amounts": [],
        "suspicious_round_numbers": [],
        "extreme_ratios": []
    }
    
    # Get basic statistics for the game
    stats = db.execute(text("""
        SELECT 
            AVG(sps.buy_in_sum) as avg_buy_in,
            STDDEV(sps.buy_in_sum) as stddev_buy_in,
            AVG(sps.cash_out_sum + sps.in_game) as avg_cash_out,
            STDDEV(sps.cash_out_sum + sps.in_game) as stddev_cash_out,
            AVG(ABS(sps.net)) as avg_abs_net,
            STDDEV(ABS(sps.net)) as stddev_abs_net
        FROM sessions s
        JOIN session_player_summaries sps ON s.id = sps.session_id
        WHERE s.game_id = :game_id
    """), {"game_id": game_id}).fetchone()
    
    if stats and stats.avg_buy_in:
        # Find amounts that are 10+ standard deviations from mean
        outlier_threshold = 10
        
        outlier_amounts = db.execute(text("""
            SELECT s.game_number, s.external_id, p.display_name,
                   sps.buy_in_sum, sps.cash_out_sum, sps.in_game, sps.net,
                   ABS(sps.buy_in_sum - :avg_buy_in) / NULLIF(:stddev_buy_in, 0) as buy_in_zscore,
                   ABS((sps.cash_out_sum + sps.in_game) - :avg_cash_out) / NULLIF(:stddev_cash_out, 0) as cash_out_zscore
            FROM sessions s
            JOIN session_player_summaries sps ON s.id = sps.session_id
            JOIN players p ON sps.player_id = p.id
            WHERE s.game_id = :game_id
            AND (ABS(sps.buy_in_sum - :avg_buy_in) / NULLIF(:stddev_buy_in, 0) > :threshold
                 OR ABS((sps.cash_out_sum + sps.in_game) - :avg_cash_out) / NULLIF(:stddev_cash_out, 0) > :threshold)
            ORDER BY GREATEST(
                ABS(sps.buy_in_sum - :avg_buy_in) / NULLIF(:stddev_buy_in, 0),
                ABS((sps.cash_out_sum + sps.in_game) - :avg_cash_out) / NULLIF(:stddev_cash_out, 0)
            ) DESC
        """), {
            "game_id": game_id,
            "avg_buy_in": float(stats.avg_buy_in),
            "stddev_buy_in": float(stats.stddev_buy_in or 1),
            "avg_cash_out": float(stats.avg_cash_out),
            "stddev_cash_out": float(stats.stddev_cash_out or 1),
            "threshold": outlier_threshold
        }).fetchall()
        
        for row in outlier_amounts:
            outliers["unusual_amounts"].append({
                "game_number": row.game_number,
                "external_id": row.external_id,
                "player_name": row.display_name,
                "buy_in": int(row.buy_in_sum),
                "cash_out_total": int(row.cash_out_sum + row.in_game),
                "net": int(row.net),
                "buy_in_zscore": round(float(row.buy_in_zscore or 0), 2),
                "cash_out_zscore": round(float(row.cash_out_zscore or 0), 2)
            })
    
    # Find suspicious round numbers (too many ending in 00)
    round_numbers = db.execute(text("""
        SELECT p.display_name,
               COUNT(*) as total_entries,
               COUNT(CASE WHEN sps.buy_in_sum % 10000 = 0 THEN 1 END) as round_buy_ins,
               COUNT(CASE WHEN (sps.cash_out_sum + sps.in_game) % 10000 = 0 THEN 1 END) as round_cash_outs
        FROM sessions s
        JOIN session_player_summaries sps ON s.id = sps.session_id
        JOIN players p ON sps.player_id = p.id
        WHERE s.game_id = :game_id
        GROUP BY p.id, p.display_name
        HAVING COUNT(*) >= 3
        AND (COUNT(CASE WHEN sps.buy_in_sum % 10000 = 0 THEN 1 END) * 1.0 / COUNT(*) > 0.7
             OR COUNT(CASE WHEN (sps.cash_out_sum + sps.in_game) % 10000 = 0 THEN 1 END) * 1.0 / COUNT(*) > 0.7)
        ORDER BY (COUNT(CASE WHEN sps.buy_in_sum % 10000 = 0 THEN 1 END) + 
                  COUNT(CASE WHEN (sps.cash_out_sum + sps.in_game) % 10000 = 0 THEN 1 END)) * 1.0 / COUNT(*) DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in round_numbers:
        outliers["suspicious_round_numbers"].append({
            "player_name": row.display_name,
            "total_entries": int(row.total_entries),
            "round_buy_ins": int(row.round_buy_ins),
            "round_cash_outs": int(row.round_cash_outs),
            "round_percentage": round((int(row.round_buy_ins) + int(row.round_cash_outs)) / (2 * int(row.total_entries)) * 100, 1)
        })
    
    return outliers


def _validate_cross_session_data(db: Session, game_id: str) -> Dict[str, Any]:
    """Validate consistency across sessions."""
    issues = {
        "external_id_conflicts": [],
        "name_variations": [],
        "session_overlaps": []
    }
    
    # Find external_id conflicts (same external_id, different display names)
    external_conflicts = db.execute(text("""
        SELECT sps1.player_id as player1_id, p1.display_name as name1, p1.external_id,
               sps2.player_id as player2_id, p2.display_name as name2,
               COUNT(DISTINCT s1.id) as sessions1,
               COUNT(DISTINCT s2.id) as sessions2
        FROM sessions s1
        JOIN session_player_summaries sps1 ON s1.id = sps1.session_id
        JOIN players p1 ON sps1.player_id = p1.id
        JOIN sessions s2 ON s2.game_id = s1.game_id
        JOIN session_player_summaries sps2 ON s2.id = sps2.session_id
        JOIN players p2 ON sps2.player_id = p2.id
        WHERE s1.game_id = :game_id
        AND p1.external_id = p2.external_id
        AND p1.external_id IS NOT NULL
        AND p1.id != p2.id
        AND p1.display_name != p2.display_name
        GROUP BY sps1.player_id, p1.display_name, p1.external_id, sps2.player_id, p2.display_name
        ORDER BY p1.external_id
    """), {"game_id": game_id}).fetchall()
    
    for row in external_conflicts:
        issues["external_id_conflicts"].append({
            "external_id": row.external_id,
            "player1": {"id": str(row.player1_id), "name": row.name1, "sessions": int(row.sessions1)},
            "player2": {"id": str(row.player2_id), "name": row.name2, "sessions": int(row.sessions2)}
        })
    
    # For name variations, use simple exact match for now to avoid PostgreSQL extension dependency
    # This will catch exact duplicates with different casing or identical names
    name_variations = db.execute(text("""
        SELECT p1.display_name as name1, p2.display_name as name2,
               p1.id as player1_id, p2.id as player2_id,
               COUNT(DISTINCT s1.id) as sessions1,
               COUNT(DISTINCT s2.id) as sessions2
        FROM sessions s1
        JOIN session_player_summaries sps1 ON s1.id = sps1.session_id
        JOIN players p1 ON sps1.player_id = p1.id
        JOIN sessions s2 ON s2.game_id = s1.game_id
        JOIN session_player_summaries sps2 ON s2.id = sps2.session_id
        JOIN players p2 ON sps2.player_id = p2.id
        WHERE s1.game_id = :game_id
        AND p1.id != p2.id
        AND (p1.external_id IS NULL OR p2.external_id IS NULL OR p1.external_id != p2.external_id)
        AND LOWER(TRIM(p1.display_name)) = LOWER(TRIM(p2.display_name))
        AND p1.display_name != p2.display_name
        GROUP BY p1.display_name, p2.display_name, p1.id, p2.id
        HAVING COUNT(DISTINCT s1.id) >= 2 OR COUNT(DISTINCT s2.id) >= 2
        ORDER BY p1.display_name
    """), {"game_id": game_id}).fetchall()
    
    for row in name_variations:
        issues["name_variations"].append({
            "player1": {"id": str(row.player1_id), "name": row.name1, "sessions": int(row.sessions1)},
            "player2": {"id": str(row.player2_id), "name": row.name2, "sessions": int(row.sessions2)}
        })
    
    return issues


def _check_business_logic_violations(db: Session, game_id: str) -> Dict[str, Any]:
    """Check for business logic violations."""
    violations = {
        "negative_amounts": [],
        "mathematical_inconsistencies": [],
        "zero_sum_violations": []
    }
    
    # Find negative buy-ins or cash-outs
    negative_amounts = db.execute(text("""
        SELECT s.game_number, s.external_id, p.display_name,
               sps.buy_in_sum, sps.cash_out_sum, sps.in_game, sps.net
        FROM sessions s
        JOIN session_player_summaries sps ON s.id = sps.session_id
        JOIN players p ON sps.player_id = p.id
        WHERE s.game_id = :game_id
        AND (sps.buy_in_sum < 0 OR sps.cash_out_sum < 0)
        ORDER BY s.game_number DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in negative_amounts:
        violations["negative_amounts"].append({
            "game_number": row.game_number,
            "external_id": row.external_id,
            "player_name": row.display_name,
            "buy_in": int(row.buy_in_sum),
            "cash_out": int(row.cash_out_sum),
            "in_game": int(row.in_game),
            "net": int(row.net)
        })
    
    # Find mathematical inconsistencies (net != cash_out + in_game - buy_in)
    math_errors = db.execute(text("""
        SELECT s.id as session_id, sps.player_id, s.game_number, s.external_id, p.display_name,
               sps.buy_in_sum, sps.cash_out_sum, sps.in_game, sps.net, sps.names,
               (sps.cash_out_sum + sps.in_game - sps.buy_in_sum) as calculated_net,
               sps.net - (sps.cash_out_sum + sps.in_game - sps.buy_in_sum) as difference
        FROM sessions s
        JOIN session_player_summaries sps ON s.id = sps.session_id
        JOIN players p ON sps.player_id = p.id
        WHERE s.game_id = :game_id
        AND sps.net != (sps.cash_out_sum + sps.in_game - sps.buy_in_sum)
        ORDER BY ABS(sps.net - (sps.cash_out_sum + sps.in_game - sps.buy_in_sum)) DESC
    """), {"game_id": game_id}).fetchall()
    
    for row in math_errors:
        violations["mathematical_inconsistencies"].append({
            "session_id": str(row.session_id),
            "player_id": str(row.player_id),
            "game_number": row.game_number,
            "external_id": row.external_id,
            "player_name": row.display_name,
            "buy_in": int(row.buy_in_sum),
            "cash_out": int(row.cash_out_sum),
            "in_game": int(row.in_game),
            "recorded_net": int(row.net),
            "calculated_net": int(row.calculated_net),
            "difference": int(row.difference),
            "names": row.names or [row.display_name]
        })
    
    return violations


def _compare_original_vs_current_data(original_json: dict, current_player_data) -> Dict[str, Any]:
    """Compare original ingested data with current session data to identify discrepancies."""
    comparison = {
        "has_differences": False,
        "missing_players": [],
        "added_players": [],
        "modified_players": [],
        "summary": {
            "original_player_count": 0,
            "current_player_count": len(current_player_data),
            "missing_count": 0,
            "added_count": 0,
            "modified_count": 0
        },
        "debug_info": {}
    }
    
    if not original_json or not isinstance(original_json, dict):
        comparison["error"] = "No original session data available"
        return comparison
    
    # Debug: Store the top-level keys of the original JSON
    comparison["debug_info"]["json_keys"] = list(original_json.keys())
    
    # Extract original player data - the structure might vary
    original_players = {}
    
    # Try different possible structures for the original data
    if "players" in original_json:
        # Direct players array
        comparison["debug_info"]["structure_used"] = "players_array"
        for player in original_json.get("players", []):
            if isinstance(player, dict):
                # Try multiple possible name fields
                name = (player.get("name") or 
                       player.get("display_name") or 
                       player.get("playerName") or 
                       player.get("player_name"))
                if name:
                    # Normalize name (strip whitespace)
                    normalized_name = name.strip()
                    original_players[normalized_name] = {
                        "buy_in_sum": int(player.get("buyInSum", 0) * 100) if player.get("buyInSum") else 0,
                        "cashOutSum": int(player.get("cashOutSum", 0) * 100) if player.get("cashOutSum") else 0,
                        "inGame": int(player.get("inGame", 0) * 100) if player.get("inGame") else 0,
                        "net": int(player.get("net", 0) * 100) if player.get("net") else 0
                    }
    elif "playerSessions" in original_json:
        # Player sessions structure
        comparison["debug_info"]["structure_used"] = "playerSessions_dict"
        for player_id, player_data in original_json.get("playerSessions", {}).items():
            if isinstance(player_data, dict):
                name = (player_data.get("playerName") or 
                       player_data.get("name") or
                       player_data.get("display_name") or
                       player_data.get("player_name"))
                if name:
                    # Normalize name (strip whitespace)
                    normalized_name = name.strip()
                    original_players[normalized_name] = {
                        "buy_in_sum": int(player_data.get("buyInSum", 0) * 100) if player_data.get("buyInSum") else 0,
                        "cashOutSum": int(player_data.get("cashOutSum", 0) * 100) if player_data.get("cashOutSum") else 0,
                        "inGame": int(player_data.get("inGame", 0) * 100) if player_data.get("inGame") else 0,
                        "net": int((player_data.get("cashOutSum", 0) + player_data.get("inGame", 0) - player_data.get("buyInSum", 0)) * 100)
                    }
    else:
        # Check if the JSON itself is the player session data or has other structures
        comparison["debug_info"]["structure_used"] = "unknown"
        # Try to iterate through the JSON looking for player-like objects
        for key, value in original_json.items():
            if isinstance(value, dict):
                # Check if this looks like player data
                name = (value.get("playerName") or 
                       value.get("name") or
                       value.get("display_name") or
                       value.get("player_name"))
                if name and any(field in value for field in ["buyInSum", "cashOutSum", "inGame"]):
                    # Normalize name (strip whitespace)
                    normalized_name = name.strip()
                    original_players[normalized_name] = {
                        "buy_in_sum": int(value.get("buyInSum", 0) * 100) if value.get("buyInSum") else 0,
                        "cashOutSum": int(value.get("cashOutSum", 0) * 100) if value.get("cashOutSum") else 0,
                        "inGame": int(value.get("inGame", 0) * 100) if value.get("inGame") else 0,
                        "net": int((value.get("cashOutSum", 0) + value.get("inGame", 0) - value.get("buyInSum", 0)) * 100)
                    }
            elif isinstance(value, list):
                # Check if this is a list of player objects
                for item in value:
                    if isinstance(item, dict):
                        name = (item.get("playerName") or 
                               item.get("name") or
                               item.get("display_name") or
                               item.get("player_name"))
                        if name and any(field in item for field in ["buyInSum", "cashOutSum", "inGame"]):
                            # Normalize name (strip whitespace)
                            normalized_name = name.strip()
                            original_players[normalized_name] = {
                                "buy_in_sum": int(item.get("buyInSum", 0) * 100) if item.get("buyInSum") else 0,
                                "cashOutSum": int(item.get("cashOutSum", 0) * 100) if item.get("cashOutSum") else 0,
                                "inGame": int(item.get("inGame", 0) * 100) if item.get("inGame") else 0,
                                "net": int(item.get("net", 0) * 100) if item.get("net") else 0
                            }
    
    comparison["summary"]["original_player_count"] = len(original_players)
    
    # Debug: Store original player names
    comparison["debug_info"]["original_players"] = list(original_players.keys())
    
    # Build current players dict by name for comparison
    current_players = {}
    for row in current_player_data:
        # Normalize the name (strip whitespace, normalize case)
        normalized_name = row.display_name.strip()
        current_players[normalized_name] = {
            "player_id": str(row.player_id),
            "buy_in_sum": int(row.buy_in_sum),
            "cash_out_sum": int(row.cash_out_sum),
            "in_game": int(row.in_game),
            "net": int(row.net)
        }
    
# Original players are already normalized during extraction
    
    # Debug: Store current player names
    comparison["debug_info"]["current_players"] = list(current_players.keys())
    comparison["debug_info"]["normalized_original_players"] = list(original_players.keys())
    
    # Find missing players (in original but not in current)
    for original_name, original_data in original_players.items():
        if original_name not in current_players:
            comparison["missing_players"].append({
                "name": original_name,
                "original_data": original_data
            })
            comparison["has_differences"] = True
    
    # Find added players (in current but not in original)
    for current_name, current_data in current_players.items():
        if current_name not in original_players:
            comparison["added_players"].append({
                "name": current_name,
                "player_id": current_data["player_id"],
                "current_data": {
                    "buy_in_sum": current_data["buy_in_sum"],
                    "cash_out_sum": current_data["cash_out_sum"],
                    "in_game": current_data["in_game"],
                    "net": current_data["net"]
                }
            })
            comparison["has_differences"] = True
    
    # Find modified players (exist in both but with different values)
    for name in set(original_players.keys()).intersection(current_players.keys()):
        original = original_players[name]
        current = current_players[name]
        
        differences = {}
        if original["buy_in_sum"] != current["buy_in_sum"]:
            differences["buy_in_sum"] = {
                "original": original["buy_in_sum"],
                "current": current["buy_in_sum"],
                "difference": current["buy_in_sum"] - original["buy_in_sum"]
            }
        
        if original["cashOutSum"] != current["cash_out_sum"]:
            differences["cash_out_sum"] = {
                "original": original["cashOutSum"],
                "current": current["cash_out_sum"],
                "difference": current["cash_out_sum"] - original["cashOutSum"]
            }
        
        if original["inGame"] != current["in_game"]:
            differences["in_game"] = {
                "original": original["inGame"],
                "current": current["in_game"],
                "difference": current["in_game"] - original["inGame"]
            }
        
        if original["net"] != current["net"]:
            differences["net"] = {
                "original": original["net"],
                "current": current["net"],
                "difference": current["net"] - original["net"]
            }
        
        if differences:
            comparison["modified_players"].append({
                "name": name,
                "player_id": current["player_id"],
                "differences": differences
            })
            comparison["has_differences"] = True
    
    # Update summary counts
    comparison["summary"]["missing_count"] = len(comparison["missing_players"])
    comparison["summary"]["added_count"] = len(comparison["added_players"])
    comparison["summary"]["modified_count"] = len(comparison["modified_players"])
    
    return comparison


def get_session_detail(session_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific session including player breakdown and audit history.
    """
    with SessionLocal() as db:
        # Get session info
        session = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get player summaries for this session
        player_data = db.execute(text("""
            SELECT 
                sps.player_id,
                p.display_name,
                sps.buy_in_sum,
                sps.cash_out_sum,
                sps.in_game,
                sps.net
            FROM session_player_summaries sps
            JOIN players p ON sps.player_id = p.id
            WHERE sps.session_id = :session_id
            ORDER BY p.display_name
        """), {"session_id": session_id}).fetchall()
        
        # Calculate session totals
        total_buy_ins = sum(row.buy_in_sum for row in player_data)
        total_cash_outs = sum(row.cash_out_sum for row in player_data)
        total_in_game = sum(row.in_game for row in player_data)
        balance = total_buy_ins - total_cash_outs - total_in_game
        
        # Get audit logs related to this session (if table exists)
        audit_entries = []
        try:
            audit_logs = db.execute(text("""
                SELECT 
                    al.id,
                    al.session_id,
                    al.actor_kind,
                    al.actor_id,
                    al.action,
                    al.target_table,
                    al.target_id,
                    al.at,
                    al.before,
                    al.after
                FROM audit_log al
                WHERE al.session_id = :session_id 
                   OR al.target_id LIKE :session_id_pattern
                ORDER BY al.at DESC
                LIMIT 20
            """), {
                "session_id": session_id,
                "session_id_pattern": f"{session_id}:%"
            }).fetchall()
            
            # Format audit logs
            for log in audit_logs:
                # Generate description based on action
                description = _get_audit_description(log.action, log.target_table, log.before, log.after)
                
                audit_entries.append({
                    "id": str(log.id),
                    "actor_kind": log.actor_kind,
                    "actor_id": log.actor_id,
                    "action": log.action,
                    "target_table": log.target_table,
                    "timestamp": log.at.isoformat() if log.at else None,
                    "description": description,
                    "before": log.before,
                    "after": log.after
                })
        except Exception as e:
            # If audit_logs table doesn't exist or query fails, just continue without audit data
            logging.warning(f"Could not fetch audit logs for session {session_id}: {e}")
            audit_entries = []
        
        # Compare original vs current data
        comparison = _compare_original_vs_current_data(session.end_session_json, player_data)

        return {
            "session_id": session.id,
            "external_id": session.external_id or "N/A",
            "game_number": session.game_number,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "players": [
                {
                    "player_id": row.player_id,
                    "display_name": row.display_name,
                    "buy_in_sum": int(row.buy_in_sum),
                    "cash_out_sum": int(row.cash_out_sum),
                    "in_game": int(row.in_game),
                    "net": int(row.net)
                }
                for row in player_data
            ],
            "totals": {
                "buy_ins": int(total_buy_ins),
                "cash_outs": int(total_cash_outs),
                "in_game": int(total_in_game),
                "balance": int(balance)
            },
            "audit_logs": audit_entries,
            "data_comparison": comparison
        }


def _get_audit_description(action: str, target_table: str, before: dict, after: dict) -> str:
    """Generate a human-readable description of the audit operation."""
    try:
        if action == 'IMPORT_LEDGER_SESSION':
            if after and 'players_count' in after:
                count = after['players_count']
                return f"Imported session with {count} players"
            return "Session imported"
        
        elif action == 'LEDGER_UPDATE':
            if before and after:
                # Check what was changed
                changes = []
                for key in after.keys():
                    if key in before and before[key] != after[key]:
                        if key == 'buy_in_sum':
                            changes.append(f"buy-in: ${before[key]/100:.2f} → ${after[key]/100:.2f}")
                        elif key == 'cash_out_sum':
                            changes.append(f"cash-out: ${before[key]/100:.2f} → ${after[key]/100:.2f}")
                        elif key == 'in_game':
                            changes.append(f"in-game: ${before[key]/100:.2f} → ${after[key]/100:.2f}")
                        elif key == 'net':
                            changes.append(f"net: ${before[key]/100:.2f} → ${after[key]/100:.2f}")
                        elif key == 'names':
                            changes.append(f"names updated")
                if changes:
                    return f"Updated ledger entry: {', '.join(changes)}"
            return "Updated ledger entry"
        
        elif action == 'LEDGER_DELETE':
            return "Deleted ledger entry"
        
        elif action.endswith('_UPDATE'):
            table = target_table.replace('_', ' ').title()
            return f"Updated {table}"
        
        elif action.endswith('_INSERT'):
            table = target_table.replace('_', ' ').title()
            return f"Created {table}"
        
        elif action.endswith('_DELETE'):
            table = target_table.replace('_', ' ').title()
            return f"Deleted {table}"
        
        else:
            # Generic description
            action_name = action.replace('_', ' ').title()
            table_name = target_table.replace('_', ' ').title()
            return f"{action_name} on {table_name}"
            
    except Exception as e:
        logging.warning(f"Failed to generate description for audit action {action}: {e}")
        return action


def recalculate_session_balance(session_id: str) -> Dict[str, Any]:
    """
    Recalculate session balance by re-summing all player entries.
    This function recalculates and fixes any mathematical errors in player entries.
    """
    with SessionLocal() as db:
        # Get session info
        session = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get all player summaries for this session
        player_summaries = db.execute(text("""
            SELECT 
                player_id,
                buy_in_sum,
                cash_out_sum,
                in_game,
                net
            FROM session_player_summaries
            WHERE session_id = :session_id
        """), {"session_id": session_id}).fetchall()

        if not player_summaries:
            raise ValueError(f"No player summaries found for session {session_id}")

        # Calculate correct totals and fix any mathematical errors
        total_buy_ins = sum(row.buy_in_sum for row in player_summaries)
        total_cash_outs = sum(row.cash_out_sum for row in player_summaries)
        total_in_game = sum(row.in_game for row in player_summaries)
        calculated_balance = total_buy_ins - total_cash_outs - total_in_game

        # Check for and fix mathematical inconsistencies in individual player records
        fixes_applied = 0
        for row in player_summaries:
            # Calculate what the net should be: cash_out + in_game - buy_in
            correct_net = row.cash_out_sum + row.in_game - row.buy_in_sum
            
            if row.net != correct_net:
                # Fix the mathematical error
                db.execute(text("""
                    UPDATE session_player_summaries 
                    SET net = :correct_net 
                    WHERE session_id = :session_id AND player_id = :player_id
                """), {
                    "correct_net": correct_net,
                    "session_id": session_id,
                    "player_id": row.player_id
                })
                fixes_applied += 1

        # Commit any fixes
        if fixes_applied > 0:
            db.commit()
            
            # Recalculate totals after fixes
            updated_summaries = db.execute(text("""
                SELECT buy_in_sum, cash_out_sum, in_game, net
                FROM session_player_summaries
                WHERE session_id = :session_id
            """), {"session_id": session_id}).fetchall()
            
            total_buy_ins = sum(row.buy_in_sum for row in updated_summaries)
            total_cash_outs = sum(row.cash_out_sum for row in updated_summaries)
            total_in_game = sum(row.in_game for row in updated_summaries)
            calculated_balance = total_buy_ins - total_cash_outs - total_in_game

        return {
            "message": "Session balance recalculated successfully",
            "session_id": session_id,
            "totals": {
                "buy_ins": int(total_buy_ins),
                "cash_outs": int(total_cash_outs),
                "in_game": int(total_in_game),
                "balance": int(calculated_balance)
            },
            "fixes_applied": fixes_applied,
            "player_count": len(player_summaries),
            "is_balanced": calculated_balance == 0
        }