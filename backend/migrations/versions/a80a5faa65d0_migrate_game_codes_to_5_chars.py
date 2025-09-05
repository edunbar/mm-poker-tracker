"""migrate_game_codes_to_5_chars

Revision ID: a80a5faa65d0
Revises: 086a82aaceef
Create Date: 2025-09-04 21:29:05.899256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a80a5faa65d0'
down_revision: Union[str, Sequence[str], None] = '086a82aaceef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate existing 6-character game codes to 5 characters."""
    # Get connection
    connection = op.get_bind()
    
    # Import the code generation function
    import base64
    import secrets
    
    def generate_short_code(length=5):
        """Generate a short, URL-safe code for public game access."""
        return base64.b32encode(secrets.token_bytes(length)).decode().strip("=").upper()[:length]
    
    # Find all games with 6-character public_codes
    result = connection.execute(sa.text("SELECT id, public_code FROM games WHERE LENGTH(public_code) = 6"))
    games_to_update = result.fetchall()
    
    print(f"Found {len(games_to_update)} games with 6-character codes to migrate")
    
    # For each game, generate a new 5-character code
    for game_id, old_code in games_to_update:
        # Generate new 5-character code, ensuring uniqueness
        max_attempts = 100
        for attempt in range(max_attempts):
            new_code = generate_short_code(5)
            
            # Check if this code already exists
            existing = connection.execute(
                sa.text("SELECT COUNT(*) FROM games WHERE public_code = :code"),
                {"code": new_code}
            ).scalar()
            
            if existing == 0:
                # Code is unique, update the game
                connection.execute(
                    sa.text("UPDATE games SET public_code = :new_code WHERE id = :game_id"),
                    {"new_code": new_code, "game_id": game_id}
                )
                print(f"Updated game {game_id}: {old_code} -> {new_code}")
                break
        else:
            raise RuntimeError(f"Failed to generate unique 5-character code for game {game_id} after {max_attempts} attempts")


def downgrade() -> None:
    """Downgrade is not supported - cannot regenerate original 6-character codes."""
    raise NotImplementedError("Cannot downgrade game code migration - original codes cannot be recovered")
