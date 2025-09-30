"""
Payment API Integration Tests

Tests payment recording, payment history, payment summaries, and settlement suggestions
through the API endpoints with full authentication and validation.
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from flask import Flask
from src.app import create_app
from src.db.database import SessionLocal
from src.db.models import Game, Player, Session as SessionModel, SessionPlayerSummary, PaymentTransaction


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def payment_test_setup():
    """Create test game with players and session data for payment testing."""
    db = SessionLocal()
    try:
        unique_id = str(uuid.uuid4())[:8].upper()

        # Create game
        game = Game(
            public_code=f"PAY{unique_id}",
            admin_code=f"payment_admin_{unique_id}",
            title=f"Payment Test Game {unique_id}"
        )
        db.add(game)
        db.flush()

        # Create players
        alice = Player(
            display_name=f"Alice Pay {unique_id}",
            external_id=f"alice_pay_{unique_id}"
        )
        bob = Player(
            display_name=f"Bob Pay {unique_id}",
            external_id=f"bob_pay_{unique_id}"
        )
        charlie = Player(
            display_name=f"Charlie Pay {unique_id}",
            external_id=f"charlie_pay_{unique_id}"
        )
        db.add_all([alice, bob, charlie])
        db.flush()

        # Create session
        session = SessionModel(
            game_id=game.id,
            external_id=f"payment_session_{unique_id}",
            session_type="test"
        )
        db.add(session)
        db.flush()

        # Create session summaries with poker results:
        # Alice wins $100, Bob loses $50, Charlie loses $50
        alice_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=alice.id,
            buy_in_sum=10000,  # $100
            cash_out_sum=20000,  # $200
            in_game=0,
            net=10000,  # Won $100
            names=[alice.display_name]
        )
        bob_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=bob.id,
            buy_in_sum=10000,  # $100
            cash_out_sum=5000,   # $50
            in_game=0,
            net=-5000,  # Lost $50
            names=[bob.display_name]
        )
        charlie_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=charlie.id,
            buy_in_sum=10000,  # $100
            cash_out_sum=5000,   # $50
            in_game=0,
            net=-5000,  # Lost $50
            names=[charlie.display_name]
        )

        db.add_all([alice_summary, bob_summary, charlie_summary])
        db.commit()

        yield {
            'game': game,
            'alice': alice,
            'bob': bob,
            'charlie': charlie,
            'session': session
        }

    finally:
        db.close()


class TestPaymentRecording:
    """Test payment recording API endpoints."""

    def test_record_payment_valid_data(self, client, payment_test_setup):
        """Record a valid payment."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 25.50,
                "payment_method": "Venmo",
                "notes": "Test payment via API",
                "reference_id": "venmo_123456"
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'id' in data
        assert 'message' in data
        assert 'Payment recorded successfully' in data['message']

        # Verify payment was actually recorded in database
        db = SessionLocal()
        try:
            payment = db.query(PaymentTransaction).filter_by(id=data['id']).first()
            assert payment is not None
            assert str(payment.payer_id) == str(bob.id)
            assert str(payment.recipient_id) == str(alice.id)
            assert payment.amount == Decimal('25.50')
            assert payment.payment_method == "Venmo"
            assert payment.notes == "Test payment via API"
            assert payment.reference_id == "venmo_123456"
        finally:
            db.close()

    def test_record_payment_minimal_data(self, client, payment_test_setup):
        """Record payment with only required fields."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        charlie = setup['charlie']

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(charlie.id),
                "recipient_id": str(alice.id),
                "amount": 30.00
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'id' in data
        assert 'message' in data

    def test_record_payment_missing_required_field(self, client, payment_test_setup):
        """Missing required field should be rejected."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(alice.id),
                # Missing recipient_id
                "amount": 50.00
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'recipient_id is required' in data['error']

    def test_record_payment_invalid_amount(self, client, payment_test_setup):
        """Invalid amount should be rejected."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        # Test negative amount
        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": -25.00
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_record_payment_zero_amount(self, client, payment_test_setup):
        """Zero amount should be rejected."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 0.00
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_record_payment_self_payment(self, client, payment_test_setup):
        """Self-payment should be rejected."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(alice.id),
                "recipient_id": str(alice.id),
                "amount": 50.00
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'cannot be the same' in data['error'].lower()

    def test_record_payment_nonexistent_player(self, client, payment_test_setup):
        """Payment to nonexistent player should be rejected."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        fake_player_id = str(uuid.uuid4())

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(alice.id),
                "recipient_id": fake_player_id,
                "amount": 50.00
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_record_payment_with_custom_date(self, client, payment_test_setup):
        """Record payment with custom payment date."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        custom_date = "2024-01-15T10:30:00Z"

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 40.00,
                "payment_date": custom_date
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'id' in data

    def test_record_payment_requires_admin_code(self, client, payment_test_setup):
        """Payment recording requires admin code."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 25.00
            }
            # No admin code header
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'X-Admin-Code header required' in data['error']


class TestPaymentRetrieval:
    """Test payment history and summary retrieval."""

    def setup_payments(self, payment_test_setup):
        """Helper to create some test payments."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']
        charlie = setup['charlie']

        db = SessionLocal()
        try:
            # Create a few test payments
            payment1 = PaymentTransaction(
                game_id=str(game.id),
                payer_id=str(bob.id),
                recipient_id=str(alice.id),
                amount_cents=2500,  # $25.00
                payment_date=datetime.now(timezone.utc),
                payment_method="Venmo",
                notes="Test payment 1",
                created_by="test_admin"
            )

            payment2 = PaymentTransaction(
                game_id=str(game.id),
                payer_id=str(charlie.id),
                recipient_id=str(alice.id),
                amount_cents=3000,  # $30.00
                payment_date=datetime.now(timezone.utc),
                payment_method="Cash",
                notes="Test payment 2",
                created_by="test_admin"
            )

            db.add_all([payment1, payment2])
            db.commit()

            return [payment1, payment2]

        finally:
            db.close()

    def test_get_payment_history(self, client, payment_test_setup):
        """Get payment history for a game."""
        self.setup_payments(payment_test_setup)
        setup = payment_test_setup
        game = setup['game']

        response = client.get(f'/api/games/{game.public_code}/payments/history')

        assert response.status_code == 200
        data = response.get_json()
        assert 'transactions' in data
        transactions = data['transactions']
        assert isinstance(transactions, list)
        assert len(transactions) >= 2  # Should have at least our test payments

        # Check payment structure
        for payment in transactions:
            required_fields = ['id', 'payer_name', 'recipient_name', 'amount',
                             'payment_date', 'payment_method', 'notes', 'reference_id']
            for field in required_fields:
                assert field in payment

    def test_get_payment_summary(self, client, payment_test_setup):
        """Get payment summary/balances for a game."""
        self.setup_payments(payment_test_setup)
        setup = payment_test_setup
        game = setup['game']

        response = client.get(f'/api/games/{game.public_code}/payments')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Should have all three players

        # Check balance structure
        for player_balance in data:
            required_fields = ['player_id', 'player_name', 'poker_net_winnings',
                             'total_paid', 'total_received', 'balance', 'realized_earnings']
            for field in required_fields:
                assert field in player_balance or hasattr(player_balance, field)

    def test_get_settlement_suggestions(self, client, payment_test_setup):
        """Get settlement suggestions for a game."""
        setup = payment_test_setup
        game = setup['game']

        response = client.get(f'/api/games/{game.public_code}/payments/settlements')

        assert response.status_code == 200
        data = response.get_json()
        assert 'settlements' in data
        settlements = data['settlements']
        assert isinstance(settlements, list)

        # Should have settlement suggestions since Bob and Charlie owe money to Alice
        # (exact number depends on optimization algorithm)
        for suggestion in settlements:
            required_fields = ['payer_id', 'payer_name', 'recipient_id',
                             'recipient_name', 'amount']
            for field in required_fields:
                assert field in suggestion or hasattr(suggestion, field)

    def test_get_payment_history_empty_game(self, client):
        """Payment history for game with no payments should return empty list."""
        # Create a minimal game without payments
        db = SessionLocal()
        try:
            unique_id = str(uuid.uuid4())[:8]
            game = Game(
                public_code=f"EMPTY{unique_id}",
                admin_code=f"empty_admin_{unique_id}",
                title="Empty Game"
            )
            db.add(game)
            db.commit()

            response = client.get(f'/api/games/{game.public_code}/payments/history')

            assert response.status_code == 200
            data = response.get_json()
            assert 'transactions' in data
            transactions = data['transactions']
            assert isinstance(transactions, list)
            assert len(transactions) == 0

        finally:
            db.close()

    def test_payment_endpoints_require_valid_public_code(self, client):
        """Payment endpoints should validate public code."""
        response = client.get('/api/games/INVALID/payments')

        # Should return empty results for invalid game rather than error
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestPaymentUpdatesAndDeletion:
    """Test payment update and deletion endpoints."""

    def create_test_payment(self, payment_test_setup):
        """Helper to create a test payment for update/delete tests."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        db = SessionLocal()
        try:
            payment = PaymentTransaction(
                game_id=str(game.id),
                payer_id=str(bob.id),
                recipient_id=str(alice.id),
                amount_cents=5000,  # $50.00
                payment_date=datetime.now(timezone.utc),
                payment_method="Test",
                notes="Payment for update test",
                created_by="test_admin"
            )
            db.add(payment)
            db.commit()
            return payment

        finally:
            db.close()

    def test_update_payment(self, client, payment_test_setup):
        """Update an existing payment."""
        payment = self.create_test_payment(payment_test_setup)
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        response = client.put(f'/api/games/{game.public_code}/payments/{payment.id}',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 75.00,
                "payment_method": "Updated Method",
                "notes": "Updated notes"
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'updated successfully' in data['message']

        # Verify payment was updated in database
        db = SessionLocal()
        try:
            updated_payment = db.query(PaymentTransaction).filter_by(id=payment.id).first()
            assert updated_payment.amount == Decimal('75.00')
            assert updated_payment.payment_method == "Updated Method"
            assert updated_payment.notes == "Updated notes"
        finally:
            db.close()

    def test_update_payment_invalid_id(self, client, payment_test_setup):
        """Update with invalid payment ID should return 404."""
        setup = payment_test_setup
        game = setup['game']
        fake_payment_id = str(uuid.uuid4())

        response = client.put(f'/api/games/{game.public_code}/payments/{fake_payment_id}',
            json={"amount": 100.00},
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_update_payment_requires_admin_code(self, client, payment_test_setup):
        """Payment update requires admin code."""
        payment = self.create_test_payment(payment_test_setup)
        setup = payment_test_setup
        game = setup['game']

        response = client.put(f'/api/games/{game.public_code}/payments/{payment.id}',
            json={"amount": 60.00}
            # No admin code
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'X-Admin-Code header required' in data['error']

    def test_delete_payment(self, client, payment_test_setup):
        """Delete an existing payment."""
        payment = self.create_test_payment(payment_test_setup)
        setup = payment_test_setup
        game = setup['game']

        response = client.delete(f'/api/games/{game.public_code}/payments/{payment.id}',
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'deleted successfully' in data['message']

        # Verify payment was deleted from database
        db = SessionLocal()
        try:
            deleted_payment = db.query(PaymentTransaction).filter_by(id=payment.id).first()
            assert deleted_payment is None
        finally:
            db.close()

    def test_delete_payment_invalid_id(self, client, payment_test_setup):
        """Delete with invalid payment ID should return 404."""
        setup = payment_test_setup
        game = setup['game']
        fake_payment_id = str(uuid.uuid4())

        response = client.delete(f'/api/games/{game.public_code}/payments/{fake_payment_id}',
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_delete_payment_requires_admin_code(self, client, payment_test_setup):
        """Payment deletion requires admin code."""
        payment = self.create_test_payment(payment_test_setup)
        setup = payment_test_setup
        game = setup['game']

        response = client.delete(f'/api/games/{game.public_code}/payments/{payment.id}')

        assert response.status_code == 401
        data = response.get_json()
        assert 'X-Admin-Code header required' in data['error']


class TestPaymentValidationEdgeCases:
    """Test edge cases and validation scenarios."""

    def test_payment_with_decimal_precision(self, client, payment_test_setup):
        """Test payment with various decimal precisions."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        # Test payment with cents
        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 123.45
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 201

        # Verify precision is preserved
        data = response.get_json()
        db = SessionLocal()
        try:
            payment = db.query(PaymentTransaction).filter_by(id=data['id']).first()
            assert payment.amount == Decimal('123.45')
        finally:
            db.close()

    def test_payment_with_excessive_precision(self, client, payment_test_setup):
        """Test payment with more than 2 decimal places."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        # Test payment with 3 decimal places (should be rounded)
        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": 123.456
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 201

        # Should round to 2 decimal places
        data = response.get_json()
        db = SessionLocal()
        try:
            payment = db.query(PaymentTransaction).filter_by(id=data['id']).first()
            # Should be rounded (exact rounding depends on implementation)
            assert payment.amount in [Decimal('123.45'), Decimal('123.46')]
        finally:
            db.close()

    def test_payment_with_very_large_amount(self, client, payment_test_setup):
        """Test payment with large amount."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        large_amount = 999999.99

        response = client.post(f'/api/games/{game.public_code}/payments',
            json={
                "payer_id": str(bob.id),
                "recipient_id": str(alice.id),
                "amount": large_amount
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [201, 400]

        if response.status_code == 201:
            data = response.get_json()
            db = SessionLocal()
            try:
                payment = db.query(PaymentTransaction).filter_by(id=data['id']).first()
                assert payment.amount == Decimal(str(large_amount))
            finally:
                db.close()

    def test_concurrent_payment_recording(self, client, payment_test_setup):
        """Test concurrent payment recording (basic test)."""
        setup = payment_test_setup
        game = setup['game']
        alice = setup['alice']
        bob = setup['bob']

        # Record two payments quickly (simulating concurrency)
        payment_data = {
            "payer_id": str(bob.id),
            "recipient_id": str(alice.id),
            "amount": 25.00
        }

        response1 = client.post(f'/api/games/{game.public_code}/payments',
            json=payment_data,
            headers={'X-Admin-Code': game.admin_code}
        )

        response2 = client.post(f'/api/games/{game.public_code}/payments',
            json=payment_data,
            headers={'X-Admin-Code': game.admin_code}
        )

        # Both should succeed (or fail gracefully)
        assert response1.status_code == 201
        assert response2.status_code == 201

        # Should have created two separate payments
        data1 = response1.get_json()
        data2 = response2.get_json()
        assert data1['id'] != data2['id']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])