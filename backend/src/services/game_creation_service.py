import base64
import secrets
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db.database import SessionLocal
from db.models import Game

logger = logging.getLogger(__name__)

def generate_short_code(length=5):
    """Generate a short, URL-safe code for public game access."""
    return base64.b32encode(secrets.token_bytes(length)).decode().strip("=").upper()[:length]

def generate_admin_token(nbytes=32):
    """Generate a long, secure token for admin access."""
    return secrets.token_urlsafe(nbytes)

def create_game(title=None):
    """
    Create a new game with generated codes.
    
    Args:
        title (str, optional): Optional title for the game
        
    Returns:
        dict: Game details including public_code, admin_code, etc.
        
    Raises:
        ValueError: If game creation fails due to validation
        RuntimeError: If database operation fails
    """
    max_retries = 10  # In case of code collisions
    
    for attempt in range(max_retries):
        try:
            with SessionLocal() as db:
                # Generate codes
                public_code = generate_short_code(5)
                admin_code = generate_admin_token(32)
                
                # Create game record
                game = Game(
                    public_code=public_code,
                    admin_code=admin_code,
                    title=title.strip() if title else None,
                    meta={}
                )
                
                db.add(game)
                db.commit()
                db.refresh(game)
                
                logger.info(f"Created new game: {game.id} with public_code: {public_code}")
                
                return {
                    "game_id": str(game.id),
                    "public_code": game.public_code,
                    "admin_code": game.admin_code,
                    "title": game.title,
                    "created_at": game.created_at.isoformat()
                }
                
        except IntegrityError as e:
            db.rollback()
            if "public_code" in str(e) and attempt < max_retries - 1:
                # Public code collision, retry with new code
                logger.warning(f"Public code collision on attempt {attempt + 1}, retrying...")
                continue
            elif "admin_code" in str(e) and attempt < max_retries - 1:
                # Admin code collision (very unlikely), retry
                logger.warning(f"Admin code collision on attempt {attempt + 1}, retrying...")
                continue
            else:
                logger.error(f"Game creation failed after {attempt + 1} attempts: {e}")
                raise RuntimeError("Failed to create game due to database constraints")
        except Exception as e:
            logger.error(f"Unexpected error creating game: {e}")
            raise RuntimeError(f"Failed to create game: {str(e)}")
    
    # If we get here, we've exceeded max retries
    raise RuntimeError("Failed to create game after multiple attempts due to code collisions")

def validate_game_title(title):
    """
    Validate game title input.
    
    Args:
        title (str): The title to validate
        
    Returns:
        str: The validated and cleaned title
        
    Raises:
        ValueError: If title is invalid
    """
    if title is None:
        return None
        
    if not isinstance(title, str):
        raise ValueError("Title must be a string")
    
    title = title.strip()
    
    if len(title) > 100:
        raise ValueError("Title must be 100 characters or less")
    
    return title if title else None