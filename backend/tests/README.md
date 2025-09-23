# Payment Ledger Backend Unit Tests

This directory contains comprehensive unit tests for the payment ledger backend services.

## Test Coverage

### Files Tested
1. **payment_service.py** - 25 tests covering:
   - Payment recording and validation
   - Payment summaries and balance calculations
   - Settlement suggestions algorithm
   - Payment history retrieval
   - Balance synchronization

2. **ledger_service.py** - 20 tests covering:
   - Session summary retrieval
   - Session summary updates
   - Session summary deletion
   - Entire session deletion
   - Payment balance updates
   - Cache invalidation

3. **ledger_analysis_service.py** - 28 tests covering:
   - Overall balance analysis
   - Session-by-session analysis
   - Player anomaly detection
   - Temporal consistency checks
   - Statistical outlier detection
   - Cross-session data validation
   - Business logic violation checks
   - Payment ledger balance verification
   - Session detail retrieval
   - Balance recalculation

## Test Results

**Total Tests: 94**
- ✅ Passing: 94 (100%)
- ❌ Failing: 0

### Test Categories

#### Payment Service Tests
- ✅ Record payment with valid data
- ✅ Validate payment constraints (same payer/recipient, amount validation)
- ✅ Handle missing entities (game, player)
- ✅ Calculate payment summaries
- ✅ Generate settlement suggestions (debt minimization algorithm)
- ✅ Retrieve payment history with pagination
- ✅ Update and sync payment balances
- ✅ Edge cases (zero winnings, string dates, precision handling)

#### Ledger Service Tests
- ✅ Retrieve all session summaries
- ✅ Update session summaries with validation
- ✅ Delete session summaries with payment balance updates
- ✅ Delete entire sessions with cascading cleanup
- ✅ Handle orphaned sessions

#### Ledger Analysis Service Tests
- ✅ Overall game balance analysis
- ✅ Session-level balance checks
- ✅ Player anomaly detection (zero buy-ins, cash-outs without buy-ins)
- ✅ Temporal consistency (future dates, duplicate game numbers, gaps)
- ✅ Statistical outlier detection
- ✅ Cross-session validation (external ID conflicts, name variations)
- ✅ Business logic violations (negative amounts, mathematical inconsistencies)
- ✅ Payment ledger balance verification
- ✅ Session detail retrieval

## Running Tests

### Run all unit tests
```bash
export PYTHONPATH=src
python -m pytest tests/unit/ -v
```

### Run specific test file
```bash
export PYTHONPATH=src
python -m pytest tests/unit/test_payment_service.py -v
```

### Run with coverage
```bash
export PYTHONPATH=src
python -m pytest tests/unit/ --cov=services --cov-report=html
```

## Test Fixtures

All tests use shared fixtures defined in `tests/conftest.py`:
- `sample_game` - Test game entity
- `sample_players` - List of test players
- `sample_session` - Test session
- `sample_session_player_summary` - Player session summary
- `sample_payment_transaction` - Payment transaction
- `sample_payment_balance` - Payment balance record
- `payment_summary_factory` - Factory for creating payment summaries
- `settlement_suggestion_factory` - Factory for settlement suggestions

## Key Test Scenarios

### Payment Recording
- Valid payment recording with method, notes, reference
- Validation of payer ≠ recipient
- Positive amount enforcement
- Entity existence validation
- Automatic balance synchronization

### Settlement Algorithm
- Simple two-player settlements
- Multi-player debt minimization
- Partial payment handling
- Small amount filtering (< $0.01)
- Already settled detection

### Data Integrity
- Zero-sum game validation
- Session balance verification
- Player activity tracking
- Orphaned record cleanup
- Payment ledger balance checks

### Edge Cases
- Zero winnings scenarios
- String date parsing
- Decimal precision handling
- Empty datasets
- Missing data handling

## Test Quality

All tests are passing with proper mocking. Tests focus on core business logic and data integrity verification.

## Future Improvements

1. Add integration tests with real database
2. Increase mock specificity for nested queries
3. Add performance benchmarks
4. Test concurrent payment scenarios
5. Add mutation testing
6. Expand edge case coverage

## Test Utilities

The test suite uses:
- `pytest` - Test framework
- `unittest.mock` - Mocking framework
- `pytest-cov` - Coverage reporting
- Custom fixtures for data setup