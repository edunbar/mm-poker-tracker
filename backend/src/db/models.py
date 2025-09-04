from sqlalchemy import (
    Column, String, Text, ForeignKey, UniqueConstraint,
    BigInteger, TIMESTAMP, func, Table, ARRAY, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB
from sqlalchemy.orm import relationship
from .database import Base

# ==========================================================
# Players Table
# ----------------------------------------------------------
# Represents a single player across all games/sessions.
#
# Columns:
# - id          : UUID primary key (server-generated with gen_random_uuid()).
# - external_id : Optional PokerNow ID or other stable identifier; unique.
# - display_name: Human-readable nickname for the player (required).
# - created_at  : Timestamp when the player record was created.
#
# Relationships:
# - games     : many-to-many association with Game via GamePlayer.
# - summaries : all SessionPlayerSummary rows for this player.
# ==========================================================
class Player(Base):
    __tablename__ = 'players'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    external_id = Column(Text, unique=True, nullable=True)  # PokerNow id if you have it
    display_name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    games = relationship('GamePlayer', back_populates='player', cascade="all, delete-orphan")
    summaries = relationship('SessionPlayerSummary', back_populates='player', cascade="all, delete-orphan")
    payments_sent = relationship('PaymentTransaction', back_populates='payer', foreign_keys='PaymentTransaction.payer_id', cascade="all, delete-orphan")
    payments_received = relationship('PaymentTransaction', back_populates='recipient', foreign_keys='PaymentTransaction.recipient_id', cascade="all, delete-orphan")
    payment_balances = relationship('PaymentBalance', back_populates='player', cascade="all, delete-orphan")


# ==========================================================
# Games Table
# ----------------------------------------------------------
# Long-lived container for multiple poker sessions.
# A game is what players will share via a short public code.
#
# Columns:
# - id          : UUID primary key.
# - public_code : Short shareable identifier (case-insensitive, CITEXT).
# - admin_code  : Secret long token; required for admin actions like importing sessions.
# - title       : Optional name/label for the game (e.g. "Thursday Night Home Game").
# - created_at  : Timestamp when the game record was created.
# - meta        : JSONB field for extra metadata or config (defaults to {}).
#
# Relationships:
# - players    : association rows linking players ↔ this game.
# - sessions   : all Session rows that belong to this game.
# - audit_logs : audit entries related to this game.
# ==========================================================
class Game(Base):
    __tablename__ = 'games'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    public_code = Column(CITEXT(), unique=True, nullable=False)
    admin_code = Column(Text, unique=True, nullable=False)  # long secret in Phase 0
    title = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    # renamed from `metadata` to avoid colliding with SQLAlchemy's declarative metadata
    meta = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    players = relationship('GamePlayer', back_populates='game', cascade="all, delete-orphan")
    sessions = relationship('Session', back_populates='game', cascade="all, delete-orphan")
    audit_logs = relationship('AuditLog', back_populates='game')
    payment_transactions = relationship('PaymentTransaction', back_populates='game', cascade="all, delete-orphan")
    payment_balances = relationship('PaymentBalance', back_populates='game', cascade="all, delete-orphan")

    __table_args__ = (
        # public_code is already UNIQUE → PG will create an index
    )


# ==========================================================
# GamePlayers Association Table
# ----------------------------------------------------------
# Links players to games. Allows tracking which players have
# participated in a given game.
#
# Columns:
# - game_id   : FK to games.id (CASCADE on delete).
# - player_id : FK to players.id (CASCADE on delete).
# - joined_at : Timestamp when the player was first linked to the game.
#
# Primary Key: (game_id, player_id)
# ==========================================================
class GamePlayer(Base):
    __tablename__ = 'game_players'
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='CASCADE'), primary_key=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='CASCADE'), primary_key=True)
    joined_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    game = relationship('Game', back_populates='players')
    player = relationship('Player', back_populates='games')


# ==========================================================
# Sessions Table
# ----------------------------------------------------------
# Represents one game session (PokerNow or live game).
#
# Columns:
# - id               : UUID primary key.
# - game_id          : FK to games.id (CASCADE on delete).
# - external_id      : Optional PokerNow session id (unique per game).
# - session_type     : 'pokernow' | 'live' to distinguish data sources.
# - session_name     : Human-readable name for live games (e.g. "Thursday Night #5").
# - game_number      : Chronological game number within the game (1, 2, 3, ...).
# - started_at       : Timestamp when the session began.
# - ended_at         : Timestamp when the session ended.
# - end_session_json : Raw JSONB copy of the session data (PokerNow or live game format).
# - created_at       : Timestamp when the session record was created.
#
# Constraints:
# - (game_id, external_id) unique, so a session ID cannot repeat in the same game.
# - (game_id, game_number) unique, so a game number cannot repeat in the same game.
#
# Relationships:
# - game       : parent Game.
# - summaries  : all SessionPlayerSummary rows for this session.
# - audit_logs : audit entries linked to this session.
# ==========================================================
class Session(Base):
    __tablename__ = 'sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    external_id = Column(Text, nullable=True)  # PokerNow session id if available
    session_type = Column(Text, nullable=False, server_default=text("'pokernow'"))  # 'pokernow' | 'live'
    session_name = Column(Text, nullable=True)  # Human-readable name for live games
    game_number = Column(BigInteger, nullable=True)  # Chronological game number within the game (1, 2, 3, ...)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    end_session_json = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    game = relationship('Game', back_populates='sessions')
    summaries = relationship('SessionPlayerSummary', back_populates='session', cascade="all, delete-orphan")
    audit_logs = relationship('AuditLog', back_populates='session')

    __table_args__ = (
        UniqueConstraint('game_id', 'external_id', name='uq_sessions_game_external'),
        UniqueConstraint('game_id', 'game_number', name='uq_sessions_game_number'),  # Ensure game_number is unique within each game
        Index('ix_sessions_game_id', 'game_id'),
        Index('ix_sessions_game_number', 'game_id', 'game_number'),  # Efficient lookups by game and number
    )


# ==========================================================
# SessionPlayerSummaries Table
# ----------------------------------------------------------
# Snapshot of a single player’s totals in a single session.
# Derived from the PokerNow players_sessions payload.
#
# Columns:
# - session_id   : FK to sessions.id (CASCADE on delete).
# - player_id    : FK to players.id (CASCADE on delete).
# - buy_in_sum   : Total buy-in chips for this session.
# - cash_out_sum : Total cash-out chips for this session.
# - in_game      : Chips still in play at session end.
# - net          : Net result = cash_out_sum + in_game - buy_in_sum.
# - names        : Array of aliases used in that session.
#
# Primary Key: (session_id, player_id)
# ==========================================================
class SessionPlayerSummary(Base):
    __tablename__ = 'session_player_summaries'

    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
    player_id  = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='CASCADE'), primary_key=True)

    buy_in_sum   = Column(BigInteger, nullable=False)
    cash_out_sum = Column(BigInteger, nullable=False)
    in_game      = Column(BigInteger, nullable=False)
    net          = Column(BigInteger, nullable=False)
    names        = Column(ARRAY(Text), nullable=False)

    session = relationship('Session', back_populates='summaries')
    player  = relationship('Player', back_populates='summaries')

    __table_args__ = (
        Index('ix_sps_session_id', 'session_id'),
        Index('ix_sps_player_id', 'player_id'),
    )


# ==========================================================
# AuditLog Table
# ----------------------------------------------------------
# Append-only log of important actions (e.g. session import).
#
# Columns:
# - id          : UUID primary key.
# - game_id     : FK to games.id (SET NULL on delete).
# - session_id  : FK to sessions.id (SET NULL on delete).
# - actor_kind  : Type of actor ('admin_code', 'system', later 'user').
# - actor_id    : Identifier of actor (e.g. admin_code hash).
# - action      : Action verb ('CREATE', 'UPDATE', 'DELETE', 'IMPORT').
# - target_table: Which table was modified.
# - target_id   : ID of target row.
# - before      : JSONB snapshot of the row before change.
# - after       : JSONB snapshot of the row after change.
# - at          : Timestamp of the action.
#
# Relationships:
# - game    : related Game (optional).
# - session : related Session (optional).
# ==========================================================
class AuditLog(Base):
    __tablename__ = 'audit_log'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='SET NULL'), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True)

    actor_kind = Column(Text, nullable=False)  # 'admin_code' | 'system'
    actor_id   = Column(Text, nullable=True)
    action     = Column(Text, nullable=False)  # 'CREATE'|'UPDATE'|'DELETE'|'IMPORT'
    target_table = Column(Text, nullable=False)
    target_id    = Column(Text, nullable=False)
    before = Column(JSONB, nullable=True)
    after  = Column(JSONB, nullable=True)
    at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    game = relationship('Game', back_populates='audit_logs')
    session = relationship('Session', back_populates='audit_logs')


# ==========================================================
# PaymentTransactions Table
# ----------------------------------------------------------
# Records peer-to-peer payments between players within a game.
#
# Columns:
# - id            : UUID primary key.
# - game_id       : FK to games.id (CASCADE on delete).
# - payer_id      : FK to players.id (CASCADE on delete).
# - recipient_id  : FK to players.id (CASCADE on delete).
# - amount_cents  : Payment amount in cents for precision.
# - payment_method: Optional payment method (Venmo, Zelle, Cash, etc.).
# - payment_date  : Date when payment was made.
# - status        : Payment status (pending, completed, cancelled).
# - notes         : Optional notes about the payment.
# - reference_id  : Optional external transaction ID.
# - created_at    : When record was created.
# - created_by    : Admin code hash for audit trail.
#
# Constraints:
# - payer_id != recipient_id (cannot pay yourself).
# - amount_cents > 0 (positive amounts only).
# ==========================================================
class PaymentTransaction(Base):
    __tablename__ = 'payment_transactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    payer_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='CASCADE'), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='CASCADE'), nullable=False)
    
    # Amount in cents (like existing system)
    amount_cents = Column(BigInteger, nullable=False)
    
    # Payment details
    payment_method = Column(Text, nullable=True)  # "Venmo", "Zelle", "Cash", etc.
    payment_date = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Status tracking
    status = Column(Text, nullable=False, server_default=text("'completed'"))  # pending, completed, cancelled
    
    # Optional references
    notes = Column(Text, nullable=True)
    reference_id = Column(Text, nullable=True)  # Venmo/Zelle transaction ID
    
    # Audit fields
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(Text, nullable=False)  # admin_code hash for audit
    
    # Relationships
    game = relationship('Game', back_populates='payment_transactions')
    payer = relationship('Player', back_populates='payments_sent', foreign_keys=[payer_id])
    recipient = relationship('Player', back_populates='payments_received', foreign_keys=[recipient_id])
    
    __table_args__ = (
        Index('ix_payment_transactions_game_date', 'game_id', 'payment_date'),
        Index('ix_payment_transactions_payer', 'payer_id'),
        Index('ix_payment_transactions_recipient', 'recipient_id'),
    )


# ==========================================================
# PaymentBalances Table
# ----------------------------------------------------------
# Cached payment balances for each player in each game.
# Updated whenever payments are recorded or poker results change.
#
# Columns:
# - id                  : UUID primary key.
# - game_id            : FK to games.id (CASCADE on delete).
# - player_id          : FK to players.id (CASCADE on delete).
# - total_paid         : Total amount paid by this player (in cents).
# - total_received     : Total amount received by this player (in cents).
# - poker_net_winnings : Net poker winnings from SessionPlayerSummary (in cents).
# - payment_balance    : Net balance: poker_net_winnings - total_paid + total_received.
# - last_updated       : When this balance was last calculated.
#
# The payment_balance represents:
# - Positive: Player is owed money
# - Negative: Player owes money
# - Zero: Player is settled up
# ==========================================================
class PaymentBalance(Base):
    __tablename__ = 'payment_balances'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='CASCADE'), nullable=False)
    
    # Running totals (in cents)
    total_paid = Column(BigInteger, nullable=False, server_default=text("0"))
    total_received = Column(BigInteger, nullable=False, server_default=text("0"))
    poker_net_winnings = Column(BigInteger, nullable=False, server_default=text("0"))  # From SessionPlayerSummary
    payment_balance = Column(BigInteger, nullable=False, server_default=text("0"))  # Net amount owed/owed to
    
    # Timestamps
    last_updated = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    game = relationship('Game', back_populates='payment_balances')
    player = relationship('Player', back_populates='payment_balances')
    
    __table_args__ = (
        UniqueConstraint('game_id', 'player_id', name='uq_payment_balances_game_player'),
        Index('ix_payment_balances_game', 'game_id'),
        Index('ix_payment_balances_balance', 'game_id', 'payment_balance'),  # For finding who owes/is owed
    )
