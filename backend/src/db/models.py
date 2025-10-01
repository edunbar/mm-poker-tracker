from decimal import Decimal
from sqlalchemy import (
    Column, String, Text, ForeignKey, UniqueConstraint,
    BigInteger, TIMESTAMP, func, Table, ARRAY, Index, text, Boolean, Numeric
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
    poker_events = relationship('PokerEvent', back_populates='player', cascade="all, delete-orphan")
    hands_won = relationship('HandSummary', back_populates='winner', cascade="all, delete-orphan")


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
    rules = relationship('GameRule', back_populates='game', cascade="all, delete-orphan")
    statistics_config = relationship('GameStatisticsConfig', back_populates='game', uselist=False, cascade="all, delete-orphan")

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
    ledger_csv_content = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    game = relationship('Game', back_populates='sessions')
    summaries = relationship('SessionPlayerSummary', back_populates='session', cascade="all, delete-orphan")
    audit_logs = relationship('AuditLog', back_populates='session')
    poker_events = relationship('PokerEvent', back_populates='session', cascade="all, delete-orphan")
    hand_summaries = relationship('HandSummary', back_populates='session', cascade="all, delete-orphan")

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
    
    # Properties for API compatibility
    @property
    def amount(self) -> Decimal:
        """Get amount as Decimal (converted from cents)."""
        return Decimal(self.amount_cents) / 100

    # Relationships
    game = relationship('Game', back_populates='payment_transactions')
    payer = relationship('Player', back_populates='payments_sent', foreign_keys=[payer_id])
    recipient = relationship('Player', back_populates='payments_received', foreign_keys=[recipient_id])
    
    __table_args__ = (
        Index('ix_payment_transactions_game_date', 'game_id', 'payment_date'),
        Index('ix_payment_transactions_payer', 'payer_id'),
        Index('ix_payment_transactions_recipient', 'recipient_id'),
        # Unique constraint on (game_id, reference_id) to prevent duplicate payments
        # Note: This constraint allows multiple NULL reference_ids (PostgreSQL behavior)
        UniqueConstraint('game_id', 'reference_id', name='uq_payment_transactions_game_reference'),
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


# ==========================================================
# GameRules Table
# ----------------------------------------------------------
# Stores rules for each game that admins can manage.
#
# Columns:
# - id          : UUID primary key.
# - game_id     : FK to games.id (CASCADE on delete).
# - title       : Rule title/name.
# - content     : Rule description/content (supports markdown).
# - order_index : Display order for rules.
# - created_at  : When the rule was created.
# - updated_at  : When the rule was last modified.
# - created_by  : Admin code hash for audit trail.
# ==========================================================
class GameRule(Base):
    __tablename__ = 'game_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='CASCADE'), nullable=False)

    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    order_index = Column(BigInteger, nullable=False, server_default=text("0"))

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(Text, nullable=False)  # admin_code hash for audit

    # Relationships
    game = relationship('Game', back_populates='rules')

    __table_args__ = (
        Index('ix_game_rules_game_order', 'game_id', 'order_index'),
    )


class PokerEvent(Base):
    __tablename__ = 'poker_events'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    hand_number = Column(BigInteger, nullable=True)
    event_type = Column(Text, nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='SET NULL'), nullable=True)
    player_name = Column(Text, nullable=True)
    amount = Column(BigInteger, nullable=True)
    cards = Column(Text, nullable=True)
    event_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)
    order_number = Column(BigInteger, nullable=True)
    raw_entry = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    session = relationship('Session', back_populates='poker_events')
    player = relationship('Player', back_populates='poker_events')

    __table_args__ = (
        Index('ix_poker_events_session_id', 'session_id'),
        Index('ix_poker_events_hand_number', 'session_id', 'hand_number'),
        Index('ix_poker_events_player_id', 'player_id'),
    )


class HandSummary(Base):
    __tablename__ = 'hand_summaries'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    hand_number = Column(BigInteger, nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    pot_size = Column(BigInteger, nullable=True)
    winner_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='SET NULL'), nullable=True)
    winner_name = Column(Text, nullable=True)
    board_cards = Column(Text, nullable=True)
    num_players = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    session = relationship('Session', back_populates='hand_summaries')
    winner = relationship('Player', back_populates='hands_won')

    __table_args__ = (
        UniqueConstraint('session_id', 'hand_number', name='uq_hand_summaries_session_hand'),
        Index('ix_hand_summaries_session_id', 'session_id'),
        Index('ix_hand_summaries_winner_id', 'winner_id'),
    )


# ==========================================================
# PlayerHandParticipation Table
# ----------------------------------------------------------
# Tracks each player's actions and participation in each hand
# for calculating poker statistics like VPIP, PFR, and AF.
#
# Columns:
# - session_id, player_id, hand_number: Unique per participation
# - was_dealt_cards: Whether player was dealt cards (denominator for stats)
# - posted_blind: Whether player posted small/big blind this hand
# - vpip_eligible: Player had opportunity to act pre-flop
# - vpip_action: Player voluntarily put money in pot pre-flop (not blinds)
# - pfr_action: Player raised or re-raised pre-flop
# - postflop_*: Counts for aggression frequency calculations
# ==========================================================
class PlayerHandParticipation(Base):
    __tablename__ = 'player_hand_participation'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='RESTRICT'), nullable=False)
    hand_number = Column(BigInteger, nullable=False)

    # Hand participation flags
    was_dealt_cards = Column(Boolean, nullable=False, server_default=text("false"))
    posted_blind = Column(Boolean, nullable=False, server_default=text("false"))
    posted_sb_amount = Column(BigInteger, nullable=True)
    posted_bb_amount = Column(BigInteger, nullable=True)

    # Pre-flop actions for VPIP/PFR
    vpip_eligible = Column(Boolean, nullable=False, server_default=text("false"))
    vpip_action = Column(Boolean, nullable=False, server_default=text("false"))
    pfr_action = Column(Boolean, nullable=False, server_default=text("false"))
    preflop_fold = Column(Boolean, nullable=False, server_default=text("false"))

    # Post-flop actions for Aggression Frequency
    postflop_actions = Column(BigInteger, nullable=False, server_default=text("0"))
    postflop_aggressive = Column(BigInteger, nullable=False, server_default=text("0"))
    postflop_passive = Column(BigInteger, nullable=False, server_default=text("0"))

    # Street breakdown for detailed analysis
    flop_actions = Column(BigInteger, nullable=False, server_default=text("0"))
    flop_aggressive = Column(BigInteger, nullable=False, server_default=text("0"))
    turn_actions = Column(BigInteger, nullable=False, server_default=text("0"))
    turn_aggressive = Column(BigInteger, nullable=False, server_default=text("0"))
    river_actions = Column(BigInteger, nullable=False, server_default=text("0"))
    river_aggressive = Column(BigInteger, nullable=False, server_default=text("0"))

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session = relationship('Session')
    player = relationship('Player')

    __table_args__ = (
        UniqueConstraint('session_id', 'player_id', 'hand_number', name='uq_player_hand_participation'),
        Index('ix_player_hand_participation_session', 'session_id'),
        Index('ix_player_hand_participation_player', 'player_id'),
        Index('ix_player_hand_participation_session_player', 'session_id', 'player_id'),
    )


# ==========================================================
# PlayerStatisticsCache Table
# ----------------------------------------------------------
# Cached aggregated poker statistics for performance.
# Updated after each session import.
#
# Columns:
# - session_id, player_id: Unique per session/player combination
# - hands_dealt: Total hands where player was dealt cards
# - vpip_hands, pfr_hands: Count of hands for VPIP/PFR
# - vpip_percentage, pfr_percentage: Calculated percentages
# - aggression_frequency: Post-flop aggression percentage
# - play_style: Classified playing style (TAG, LAG, TP, LP)
# ==========================================================
class PlayerStatisticsCache(Base):
    __tablename__ = 'player_statistics_cache'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey('players.id', ondelete='RESTRICT'), nullable=False)

    # Hand counts for percentage calculations
    hands_dealt = Column(BigInteger, nullable=False, server_default=text("0"))
    vpip_hands = Column(BigInteger, nullable=False, server_default=text("0"))
    pfr_hands = Column(BigInteger, nullable=False, server_default=text("0"))
    postflop_hands = Column(BigInteger, nullable=False, server_default=text("0"))

    # Action counts for aggression frequency
    postflop_total_actions = Column(BigInteger, nullable=False, server_default=text("0"))
    postflop_aggressive_actions = Column(BigInteger, nullable=False, server_default=text("0"))
    postflop_passive_actions = Column(BigInteger, nullable=False, server_default=text("0"))

    # Calculated percentages (stored for performance)
    vpip_percentage = Column(Numeric(5, 2), nullable=True)
    pfr_percentage = Column(Numeric(5, 2), nullable=True)
    aggression_frequency = Column(Numeric(5, 2), nullable=True)

    # Street-specific aggression frequencies
    flop_af = Column(Numeric(5, 2), nullable=True)
    turn_af = Column(Numeric(5, 2), nullable=True)
    river_af = Column(Numeric(5, 2), nullable=True)

    # Play style classification
    play_style = Column(Text, nullable=True)

    # Timestamps
    calculated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    session = relationship('Session')
    player = relationship('Player')

    __table_args__ = (
        UniqueConstraint('session_id', 'player_id', name='uq_player_statistics_cache'),
        Index('ix_player_statistics_session', 'session_id'),
        Index('ix_player_statistics_player', 'player_id'),
        Index('ix_player_statistics_vpip', 'vpip_percentage'),
        Index('ix_player_statistics_pfr', 'pfr_percentage'),
        Index('ix_player_statistics_style', 'play_style'),
    )


# ==========================================================
# Game Statistics Configuration Table
# ----------------------------------------------------------
# Stores configurable thresholds for poker statistics
# classification based on game type (tournament, cash, etc.)
#
# Allows each game to have customized classification thresholds
# that make sense for that specific game type and player pool.
# ==========================================================

class GameStatisticsConfig(Base):
    __tablename__ = 'game_statistics_config'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    game_id = Column(UUID(as_uuid=True), ForeignKey('games.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Configuration type
    config_name = Column(String(50), nullable=False, server_default="'friendlyHighStack'")

    # VPIP thresholds (percentages)
    vpip_tight_threshold = Column(BigInteger, nullable=False, server_default="45")      # Below this = tight
    vpip_normal_threshold = Column(BigInteger, nullable=False, server_default="55")     # Below this = normal
    vpip_loose_threshold = Column(BigInteger, nullable=False, server_default="65")      # Below this = loose, above = very loose

    # PFR thresholds (percentages)
    pfr_passive_threshold = Column(BigInteger, nullable=False, server_default="10")     # Below this = passive
    pfr_normal_threshold = Column(BigInteger, nullable=False, server_default="20")      # Below this = normal
    pfr_aggressive_threshold = Column(BigInteger, nullable=False, server_default="30")  # Above this = very aggressive

    # AF thresholds (percentages)
    af_passive_threshold = Column(BigInteger, nullable=False, server_default="30")      # Below this = passive
    af_aggressive_threshold = Column(BigInteger, nullable=False, server_default="45")   # Above this = aggressive

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    game = relationship("Game", back_populates="statistics_config")

    __table_args__ = (
        Index('ix_game_statistics_config_game_id', 'game_id'),
        Index('ix_game_statistics_config_type', 'config_name'),
    )
