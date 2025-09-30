# Domain Layer Migration Guide

This guide provides step-by-step instructions for migrating your existing poker tracker application from a service-based architecture to a clean Domain-Driven Design (DDD) architecture.

## Overview

The new domain layer introduces:
- **Domain Entities**: `PokerSession` with pure business logic
- **Value Objects**: `Money`, `SessionId`, etc. for type safety
- **Repository Pattern**: Decoupled persistence layer
- **Application Services**: Orchestrate domain operations
- **Domain Events**: Enable loose coupling and event-driven architecture

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

#### 1.1 Install the Domain Layer Files

All domain layer files have been created in the following structure:
```
backend/src/
├── domain/
│   └── poker/
│       ├── entities/
│       │   └── poker_session.py
│       ├── value_objects.py
│       ├── exceptions.py
│       ├── events.py
│       └── repositories.py
├── application/
│   └── use_cases/
│       └── end_poker_session.py
├── infrastructure/
│   └── persistence/
│       └── sqlalchemy/
│           └── poker_repository.py
└── tests/
    └── unit/
        └── domain/
            ├── test_value_objects.py
            └── test_poker_session.py
```

#### 1.2 Add Dependencies

Add these to your `requirements.txt`:
```
# Already included if using SQLAlchemy and Flask
pytest>=7.0.0  # For running tests
```

#### 1.3 Update Python Path

Ensure your application can import the new modules. If you're running tests from the backend directory:
```bash
export PYTHONPATH=./src:$PYTHONPATH
```

Or add this to your test configuration.

### Phase 2: Validation and Testing (Week 1-2)

#### 2.1 Run Unit Tests

Verify the domain layer works correctly:
```bash
cd backend
python -m pytest tests/unit/domain/ -v
```

Expected output:
```
tests/unit/domain/test_value_objects.py::TestMoney::test_create_money_from_various_types PASSED
tests/unit/domain/test_value_objects.py::TestMoney::test_money_precision_rounding PASSED
... (more tests)
tests/unit/domain/test_poker_session.py::TestPokerSessionCreation::test_create_poker_session_with_valid_data PASSED
... (more tests)
```

#### 2.2 Test Repository Integration

Create a simple integration test to verify the repository works with your database:

```python
# test_repository_integration.py
from src.infrastructure.persistence.sqlalchemy.poker_repository import SQLAlchemyPokerSessionRepository
from src.domain.poker.entities.poker_session import PokerSession
from src.domain.poker.value_objects import SessionId, PlayerId, GameId, Money
from src.db.database import SessionLocal

def test_repository_integration():
    db_session = SessionLocal()
    repository = SQLAlchemyPokerSessionRepository(db_session)

    # Create a test session
    session = PokerSession(
        session_id=SessionId.generate(),
        player_id=PlayerId("existing-player-uuid"),  # Use a real player ID from your DB
        game_id=GameId("TESTG"),  # Use a real game ID from your DB
        buy_in_amount=Money("100.00"),
        session_type="cash_game"
    )

    # Save and retrieve
    repository.save(session)
    retrieved = repository.find_by_id(session.session_id)

    assert retrieved is not None
    assert retrieved.buy_in_amount == Money("100.00")

    db_session.close()
```

### Phase 3: Migrate First Service (Week 2-3)

#### 3.1 Choose Target Service

Start with `live_game_service.py` as it's mentioned in your requirements. This service should be migrated to use the new `EndPokerSessionUseCase`.

#### 3.2 Create Domain Service Adapter

Create an adapter that allows your existing Flask routes to use the new domain layer:

```python
# src/adapters/live_game_adapter.py
from typing import Dict, Any
from flask import current_app
from sqlalchemy.orm import Session

from ..application.use_cases.end_poker_session import (
    EndPokerSessionUseCase,
    EndPokerSessionCommand,
    EndPokerSessionError
)
from ..infrastructure.persistence.sqlalchemy.poker_repository import SQLAlchemyPokerSessionRepository
from ..db.database import SessionLocal

class LiveGameAdapter:
    """Adapter to integrate domain layer with Flask application."""

    def __init__(self, db_session: Session = None):
        self.db_session = db_session or SessionLocal()
        self.repository = SQLAlchemyPokerSessionRepository(self.db_session)
        self.use_case = EndPokerSessionUseCase(
            session_repository=self.repository,
            # Add other services as needed
        )

    def end_session(self, session_id: str, cash_out_amount: float) -> Dict[str, Any]:
        """
        End a poker session using the domain layer.

        Args:
            session_id: Session identifier
            cash_out_amount: Cash out amount in dollars

        Returns:
            Dictionary with session results

        Raises:
            EndPokerSessionError: If the operation fails
        """
        try:
            command = EndPokerSessionCommand(
                session_id=session_id,
                cash_out_amount=str(cash_out_amount)
            )

            result = self.use_case.execute(command)

            return {
                'success': True,
                'session_id': result.session_id,
                'profit': float(result.profit),
                'hourly_rate': float(result.hourly_rate),
                'duration_minutes': result.session_duration_minutes,
                'is_profitable': result.is_profitable,
                'is_large_win': result.is_large_win,
            }

        except EndPokerSessionError as e:
            current_app.logger.error(f"Domain error ending session: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'error_code': e.error_code
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error ending session: {e}")
            return {
                'success': False,
                'error': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            }

    def __del__(self):
        if hasattr(self, 'db_session'):
            self.db_session.close()
```

#### 3.3 Update Flask Route

Modify your existing Flask route to use the adapter:

```python
# Before (in your routes file)
from ..services.live_game_service import LiveGameService

@app.route('/api/sessions/<session_id>/end', methods=['POST'])
def end_session(session_id):
    try:
        data = request.get_json()
        cash_out_amount = data['cash_out_amount']

        service = LiveGameService()
        result = service.end_session(session_id, cash_out_amount)

        return jsonify({'success': True, 'session': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# After (using domain layer)
from ..adapters.live_game_adapter import LiveGameAdapter

@app.route('/api/sessions/<session_id>/end', methods=['POST'])
def end_session(session_id):
    data = request.get_json()
    cash_out_amount = data['cash_out_amount']

    adapter = LiveGameAdapter()
    result = adapter.end_session(session_id, cash_out_amount)

    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400
```

#### 3.4 Maintain Backward Compatibility

Keep the old service running alongside the new domain layer during the transition:

```python
# Feature flag approach
from flask import current_app

@app.route('/api/sessions/<session_id>/end', methods=['POST'])
def end_session(session_id):
    data = request.get_json()
    cash_out_amount = data['cash_out_amount']

    use_domain_layer = current_app.config.get('USE_DOMAIN_LAYER', False)

    if use_domain_layer:
        # New domain layer approach
        adapter = LiveGameAdapter()
        result = adapter.end_session(session_id, cash_out_amount)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    else:
        # Legacy service approach
        try:
            service = LiveGameService()
            result = service.end_session(session_id, cash_out_amount)
            return jsonify({'success': True, 'session': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
```

### Phase 4: Gradual Service Migration (Weeks 3-6)

#### 4.1 Migration Order

Migrate services in this order (from least to most complex):
1. ✅ `live_game_service.py` (already started)
2. `session_ingestion_service.py`
3. `game_summary_service.py`
4. `ledger_service.py`
5. `player_verification_service.py`
6. `transaction_service.py`
7. `game_creation_service.py`
8. `payment_service.py`

#### 4.2 For Each Service Migration

Follow this pattern:

1. **Analyze Business Logic**: Identify what belongs in the domain vs application layer
2. **Create Use Cases**: Extract orchestration logic into application use cases
3. **Create Adapters**: Build adapters for Flask integration
4. **Add Feature Flags**: Enable A/B testing between old and new implementations
5. **Write Integration Tests**: Test the full stack with the new code
6. **Monitor and Validate**: Ensure the new implementation works correctly
7. **Remove Old Code**: Clean up once confident

#### 4.3 Example: Session Ingestion Service

```python
# New use case: src/application/use_cases/ingest_poker_session.py
class IngestPokerSessionUseCase:
    def __init__(self, session_repository: PokerSessionRepository):
        self._repository = session_repository

    def execute(self, command: IngestPokerSessionCommand) -> IngestPokerSessionResult:
        # Parse PokerNow data
        session_data = self._parse_poker_now_data(command.raw_data)

        # Create domain entity
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(command.player_id),
            game_id=GameId(command.game_id),
            buy_in_amount=Money(session_data['buy_in']),
            session_type=session_data['type']
        )

        # Add hands
        for hand_data in session_data['hands']:
            hand = Hand(
                hand_number=hand_data['number'],
                pot_size=Money(hand_data['pot']),
                player_result=Money(hand_data['result'])
            )
            session.add_hand(hand)

        # End session if complete
        if session_data['ended']:
            session.end_session(Money(session_data['cash_out']))

        # Persist
        self._repository.save(session)

        return IngestPokerSessionResult(
            session_id=str(session.session_id),
            hands_imported=len(session_data['hands']),
            total_profit=str(session.calculate_profit().amount)
        )
```

### Phase 5: Advanced Features (Weeks 6-8)

#### 5.1 Implement Event Publishing

Add real event publishing for domain events:

```python
# src/infrastructure/events/event_publisher.py
from typing import List
import json
from ..domain.poker.events import DomainEvent

class DatabaseEventPublisher:
    """Store events in database for later processing."""

    def __init__(self, db_session):
        self.db_session = db_session

    def publish_events(self, events: List[DomainEvent]) -> None:
        for event in events:
            # Store in events table for async processing
            event_record = EventStore(
                event_id=event.event_id,
                event_type=event.event_type(),
                event_data=json.dumps(event.to_dict()),
                occurred_at=event.occurred_at
            )
            self.db_session.add(event_record)

        self.db_session.commit()

class RedisEventPublisher:
    """Publish events to Redis for real-time processing."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def publish_events(self, events: List[DomainEvent]) -> None:
        for event in events:
            self.redis.publish(
                f"poker.events.{event.event_type()}",
                json.dumps(event.to_dict())
            )
```

#### 5.2 Add Payment Integration

Implement real payment processing:

```python
# src/infrastructure/payments/stripe_payment_processor.py
import stripe
from ...domain.poker.value_objects import Money

class StripePaymentProcessor:
    def __init__(self, api_key: str):
        stripe.api_key = api_key

    def process_profitable_session(self, session_id: str, profit_amount: Money) -> bool:
        try:
            # Create payment intent for house rake or player payout
            intent = stripe.PaymentIntent.create(
                amount=int(profit_amount.amount * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'session_id': session_id,
                    'type': 'session_profit'
                }
            )
            return intent.status == 'succeeded'
        except stripe.error.StripeError:
            return False
```

#### 5.3 Performance Optimization

Add caching and query optimization:

```python
# src/infrastructure/persistence/sqlalchemy/cached_poker_repository.py
from functools import lru_cache
from ...domain.poker.repositories import PokerSessionRepository

class CachedPokerSessionRepository:
    def __init__(self, base_repository: PokerSessionRepository, cache_size=128):
        self._repository = base_repository
        self._find_by_id = lru_cache(maxsize=cache_size)(self._repository.find_by_id)

    def find_by_id(self, session_id):
        return self._find_by_id(session_id)

    def save(self, session):
        result = self._repository.save(session)
        # Invalidate cache for this session
        self._find_by_id.cache_clear()
        return result
```

### Phase 6: Cleanup and Optimization (Week 8)

#### 6.1 Remove Legacy Services

Once all services are migrated and tested:

1. Remove old service files
2. Clean up unused imports
3. Update documentation
4. Remove feature flags

#### 6.2 Database Migrations

If you need to modify the database schema:

```python
# Create Alembic migration
# alembic revision --autogenerate -m "add_domain_events_table"

"""add domain events table

Revision ID: abc123
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('domain_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('occurred_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('domain_events')
```

## Configuration Updates

### Environment Variables

Add these configuration options:

```bash
# .env
USE_DOMAIN_LAYER=true
ENABLE_DOMAIN_EVENTS=true
ENABLE_PAYMENT_PROCESSING=false
DOMAIN_EVENT_PUBLISHER=database  # or 'redis'
```

### Flask Configuration

```python
# config.py
class Config:
    USE_DOMAIN_LAYER = os.getenv('USE_DOMAIN_LAYER', 'false').lower() == 'true'
    ENABLE_DOMAIN_EVENTS = os.getenv('ENABLE_DOMAIN_EVENTS', 'false').lower() == 'true'
    ENABLE_PAYMENT_PROCESSING = os.getenv('ENABLE_PAYMENT_PROCESSING', 'false').lower() == 'true'
```

## Testing Strategy

### Unit Tests
- Run domain tests frequently: `pytest tests/unit/domain/`
- Ensure 100% coverage of domain logic
- Test all business rules and edge cases

### Integration Tests
```python
# tests/integration/test_end_session_flow.py
def test_end_session_complete_flow():
    """Test complete end session flow with database."""
    # Setup
    db_session = SessionLocal()
    repository = SQLAlchemyPokerSessionRepository(db_session)
    use_case = EndPokerSessionUseCase(repository)

    # Execute
    command = EndPokerSessionCommand(
        session_id="test-session-id",
        cash_out_amount="150.00"
    )
    result = use_case.execute(command)

    # Verify
    assert result.is_profitable

    # Cleanup
    db_session.close()
```

### Performance Tests
- Load test with concurrent session operations
- Monitor memory usage with domain entities
- Test database query performance

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Disable `USE_DOMAIN_LAYER` flag
2. **Gradual Rollback**: Revert specific services one by one
3. **Data Integrity**: Ensure no data loss during rollback
4. **Monitoring**: Watch for errors after rollback

## Success Metrics

Track these metrics to measure migration success:

- **Code Quality**: Reduced cyclomatic complexity in services
- **Test Coverage**: Increased unit test coverage (aim for 95%+)
- **Performance**: Response times should remain same or improve
- **Errors**: No increase in production errors
- **Maintainability**: Easier to add new features

## Common Issues and Solutions

### Issue: Import Errors
```
ModuleNotFoundError: No module named 'src.domain'
```
**Solution**: Add `src` to PYTHONPATH or use relative imports

### Issue: Repository Connection Errors
```
RepositoryConnectionError: Database connection failed
```
**Solution**: Ensure proper database session management and connection pooling

### Issue: Domain Event Performance
```
Slow response times due to event publishing
```
**Solution**: Make event publishing async or use background workers

### Issue: Money Precision Errors
```
Decimal precision issues in calculations
```
**Solution**: Always use Money value object, never float arithmetic

## Next Steps

After completing this migration:

1. **Extend Domain Model**: Add more entities (Player, Game, Tournament)
2. **Add Business Rules**: Implement more complex poker business logic
3. **Event Sourcing**: Consider event sourcing for audit trails
4. **CQRS**: Separate read/write models for better performance
5. **Microservices**: Extract domain services to separate microservices

## Support

If you encounter issues during migration:

1. Check the unit tests - they demonstrate correct usage
2. Review the domain exceptions for business rule violations
3. Use the adapter pattern to integrate with existing code
4. Start with feature flags for safe deployment

The domain layer is designed to be framework-agnostic and testable. Focus on the business logic first, then integrate with your existing infrastructure.

---

**Remember**: This migration should be done incrementally. Don't try to migrate everything at once. Start with one service, validate it works correctly, then move to the next one.