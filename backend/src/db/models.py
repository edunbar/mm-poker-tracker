from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True)
    players = relationship("Player", back_populates="game")

class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    game_id = Column(Integer, ForeignKey('games.id'))

    game = relationship("Game", back_populates="players")