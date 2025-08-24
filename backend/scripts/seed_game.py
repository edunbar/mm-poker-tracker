# backend/scripts/seed_game.py
import base64, secrets
from sqlalchemy.orm import Session
from db.database import engine
from db.models import Game

def short_code(n=6):
  return base64.b32encode(secrets.token_bytes(n)).decode().strip("=").upper()[:n]

def long_token(nbytes=32):
  return secrets.token_urlsafe(nbytes)

if __name__ == "__main__":
  with Session(engine, future=True) as s:
    g = Game(
      public_code=short_code(6),
      admin_code=long_token(32),
      title="Meow Meow Poker Game",
      meta={}
    )
    s.add(g)
    s.commit()
    s.refresh(g)
    print("Game ID     :", g.id)
    print("PUBLIC CODE :", g.public_code)
    print("ADMIN CODE  :", g.admin_code)