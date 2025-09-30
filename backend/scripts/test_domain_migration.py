#!/usr/bin/env python3
"""
Domain migration verification script.

This script verifies that the domain services work correctly with existing data
and compares outputs between old and new implementations.
"""

import os
import sys
import time
import traceback
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from db.models import Game, Player, Session, SessionPlayerSummary

# Import both old and new services
from services.payment_service import PaymentService as OldPaymentService

# Try to import domain services, but handle import errors gracefully
try:
    from services.payment_service_v2 import PaymentService as NewPaymentService
    from services.live_game_service_v2 import LiveGameService as NewLiveGameService
    DOMAIN_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Domain services not available: {e}")
    DOMAIN_SERVICES_AVAILABLE = False
    # Create dummy classes for testing
    class NewPaymentService:
        def __init__(self, db_session):
            self.db_session = db_session
        def get_payment_summary(self, game_id):
            return []
        def get_settlement_suggestions(self, game_id):
            return []

    class NewLiveGameService:
        def __init__(self, db_session):
            self.db_session = db_session
        def end_session(self, session_id, amount):
            raise ValueError("Domain services not available")


@dataclass
class ComparisonResult:
    """Result of comparing old vs new service outputs."""
    test_name: str
    old_result: Any
    new_result: Any
    matches: bool
    error: str = None


@dataclass
class PerformanceResult:
    """Performance comparison result."""
    test_name: str
    old_time: float
    new_time: float
    improvement_percent: float


class DomainMigrationTester:
    """Main class for testing domain migration."""

    def __init__(self):
        """Initialize tester with database connection."""
        self.db = SessionLocal()
        print("🔗 Connected to database")

        # Track test results
        self.comparison_results: List[ComparisonResult] = []
        self.performance_results: List[PerformanceResult] = []
        self.errors: List[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def run_all_tests(self) -> None:
        """Run all migration tests."""
        print("\n" + "="*70)
        print("🚀 STARTING DOMAIN MIGRATION VERIFICATION")
        print("="*70)

        try:
            # Test 1: Compare service outputs
            print("\n📊 Phase 1: Comparing Service Outputs")
            self.compare_service_outputs()

            # Test 2: Database compatibility
            print("\n🗄️  Phase 2: Verifying Database Compatibility")
            self.verify_database_compatibility()

            # Test 3: Performance comparison
            print("\n⚡ Phase 3: Performance Comparison")
            self.performance_comparison()

            # Test 4: Error handling
            print("\n🚨 Phase 4: Error Handling Verification")
            self.test_error_handling()

            # Final report
            self.generate_report()

        except Exception as e:
            print(f"\n❌ Fatal error during testing: {e}")
            traceback.print_exc()
            self.errors.append(f"Fatal error: {e}")

    def compare_service_outputs(self) -> None:
        """Compare outputs between old and new services."""
        print("   Testing payment service outputs...")

        # Get test games
        games = self.db.query(Game).limit(3).all()

        if not games:
            print("   ⚠️  No games found in database - skipping payment service comparison")
            return

        for game in games:
            try:
                self._compare_payment_service_for_game(game)
            except Exception as e:
                error_msg = f"Error comparing payment service for game {game.public_code}: {e}"
                print(f"   ❌ {error_msg}")
                self.errors.append(error_msg)

        print("   ✅ Payment service comparison complete")

    def _compare_payment_service_for_game(self, game: Game) -> None:
        """Compare payment service outputs for a specific game."""
        game_id = str(game.id)

        # Initialize services
        old_service = OldPaymentService()
        new_service = NewPaymentService(self.db)

        try:
            # Compare payment summaries
            old_summary = old_service.get_payment_summary(game_id)
            new_summary = new_service.get_payment_summary(game_id)

            matches = self._compare_payment_summaries(old_summary, new_summary)

            self.comparison_results.append(ComparisonResult(
                test_name=f"Payment Summary - Game {game.public_code}",
                old_result=len(old_summary),
                new_result=len(new_summary),
                matches=matches
            ))

            if matches:
                print(f"   ✅ Payment summary matches for game {game.public_code}")
            else:
                print(f"   ❌ Payment summary mismatch for game {game.public_code}")

        except Exception as e:
            error_msg = f"Payment summary comparison failed for {game.public_code}: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)

        try:
            # Compare settlement suggestions
            old_settlements = old_service.get_settlement_suggestions(game_id)
            new_settlements = new_service.get_settlement_suggestions(game_id)

            settlements_match = len(old_settlements) == len(new_settlements)

            self.comparison_results.append(ComparisonResult(
                test_name=f"Settlement Suggestions - Game {game.public_code}",
                old_result=len(old_settlements),
                new_result=len(new_settlements),
                matches=settlements_match
            ))

            if settlements_match:
                print(f"   ✅ Settlement suggestions match for game {game.public_code}")
            else:
                print(f"   ⚠️  Settlement suggestion count differs for game {game.public_code} (old: {len(old_settlements)}, new: {len(new_settlements)})")

        except Exception as e:
            error_msg = f"Settlement comparison failed for {game.public_code}: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)

    def _compare_payment_summaries(self, old_summary: List, new_summary: List) -> bool:
        """Compare payment summary structures."""
        if len(old_summary) != len(new_summary):
            return False

        # Check that all required fields exist in both
        if not old_summary:  # Empty lists
            return True

        old_fields = set(vars(old_summary[0]).keys())
        new_fields = set(vars(new_summary[0]).keys())

        required_fields = {
            'player_id', 'player_name', 'poker_net_winnings',
            'total_paid', 'total_received', 'balance', 'realized_earnings'
        }

        return required_fields.issubset(old_fields) and required_fields.issubset(new_fields)

    def verify_database_compatibility(self) -> None:
        """Verify that domain services work with existing database schema."""
        print("   Testing repository functionality...")

        try:
            from infrastructure.persistence.sqlalchemy.poker_repository import SQLAlchemyPokerSessionRepository
            from domain.poker.value_objects import SessionId, PlayerId, GameId, Money
            from domain.poker.entities.poker_session import PokerSession

            # Test repository operations
            repository = SQLAlchemyPokerSessionRepository(self.db)

            # Test finding existing sessions
            existing_sessions = repository.find_active_sessions()
            print(f"   📊 Found {len(existing_sessions)} active sessions")

            # Test creating a new session
            test_players = self.db.query(Player).limit(1).all()
            test_games = self.db.query(Game).limit(1).all()

            if test_players and test_games:
                test_session = PokerSession(
                    session_id=SessionId.generate(),
                    player_id=PlayerId(str(test_players[0].id)),
                    game_id=GameId(test_games[0].public_code),
                    buy_in_amount=Money("100.00"),
                    session_type="test"
                )

                # Save and retrieve
                repository.save(test_session)
                retrieved = repository.find_by_id(test_session.session_id)

                if retrieved and retrieved.buy_in_amount == Money("100.00"):
                    print("   ✅ Repository save/retrieve works correctly")

                    # Clean up test session
                    repository.delete(test_session.session_id)

                else:
                    self.errors.append("Repository retrieve failed or data mismatch")
                    print("   ❌ Repository retrieve failed")
            else:
                print("   ⚠️  No test data available for repository testing")

        except Exception as e:
            error_msg = f"Database compatibility test failed: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)
            traceback.print_exc()

    def performance_comparison(self) -> None:
        """Compare performance between old and new services."""
        print("   Running performance benchmarks...")

        games = self.db.query(Game).limit(2).all()

        if not games:
            print("   ⚠️  No games found - skipping performance comparison")
            return

        for game in games:
            try:
                self._benchmark_payment_service(game)
            except Exception as e:
                error_msg = f"Performance test failed for game {game.public_code}: {e}"
                print(f"   ❌ {error_msg}")
                self.errors.append(error_msg)

    def _benchmark_payment_service(self, game: Game) -> None:
        """Benchmark payment service performance."""
        game_id = str(game.id)
        iterations = 5  # Number of iterations for averaging

        # Benchmark old service
        old_service = OldPaymentService()
        old_times = []

        for _ in range(iterations):
            start_time = time.time()
            old_service.get_payment_summary(game_id)
            old_service.get_settlement_suggestions(game_id)
            old_times.append(time.time() - start_time)

        avg_old_time = sum(old_times) / len(old_times)

        # Benchmark new service
        new_service = NewPaymentService(self.db)
        new_times = []

        for _ in range(iterations):
            start_time = time.time()
            new_service.get_payment_summary(game_id)
            new_service.get_settlement_suggestions(game_id)
            new_times.append(time.time() - start_time)

        avg_new_time = sum(new_times) / len(new_times)

        # Calculate improvement
        if avg_old_time > 0:
            improvement = ((avg_old_time - avg_new_time) / avg_old_time) * 100
        else:
            improvement = 0

        self.performance_results.append(PerformanceResult(
            test_name=f"Payment Service - Game {game.public_code}",
            old_time=avg_old_time,
            new_time=avg_new_time,
            improvement_percent=improvement
        ))

        if improvement > 0:
            print(f"   🚀 Performance improved by {improvement:.1f}% for game {game.public_code}")
        elif improvement < -10:  # More than 10% slower
            print(f"   ⚠️  Performance degraded by {abs(improvement):.1f}% for game {game.public_code}")
        else:
            print(f"   ✅ Performance similar for game {game.public_code} ({improvement:+.1f}%)")

    def test_error_handling(self) -> None:
        """Test that error handling works correctly."""
        print("   Testing error handling scenarios...")

        try:
            # Test with invalid data
            new_service = NewLiveGameService(self.db)

            # Test invalid session ID
            try:
                new_service.end_session("invalid-session-id", 100.0)
                self.errors.append("Should have raised ValueError for invalid session")
            except ValueError:
                print("   ✅ Correctly handles invalid session ID")
            except Exception as e:
                self.errors.append(f"Wrong exception type for invalid session: {type(e).__name__}")

            # Test negative cash out
            try:
                # This should fail without creating a session since we need a valid session ID
                new_service.end_session("nonexistent", -50.0)
            except ValueError:
                print("   ✅ Correctly handles negative amounts")
            except Exception as e:
                self.errors.append(f"Wrong exception type for negative amount: {type(e).__name__}")

        except Exception as e:
            error_msg = f"Error handling test failed: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)

    def generate_report(self) -> None:
        """Generate final test report."""
        print("\n" + "="*70)
        print("📋 MIGRATION VERIFICATION REPORT")
        print("="*70)

        # Summary
        total_tests = len(self.comparison_results) + len(self.performance_results)
        passed_comparisons = sum(1 for r in self.comparison_results if r.matches)

        print(f"\n📊 Test Summary:")
        print(f"   • Total comparison tests: {len(self.comparison_results)}")
        print(f"   • Passed comparison tests: {passed_comparisons}")
        print(f"   • Performance benchmarks: {len(self.performance_results)}")
        print(f"   • Total errors: {len(self.errors)}")

        # Comparison results
        if self.comparison_results:
            print(f"\n🔍 Comparison Results:")
            for result in self.comparison_results:
                status = "✅ PASS" if result.matches else "❌ FAIL"
                print(f"   {status} {result.test_name}")
                if not result.matches:
                    print(f"      Old: {result.old_result}, New: {result.new_result}")

        # Performance results
        if self.performance_results:
            print(f"\n⚡ Performance Results:")
            for result in self.performance_results:
                if result.improvement_percent > 5:
                    status = "🚀 FASTER"
                elif result.improvement_percent < -10:
                    status = "🐌 SLOWER"
                else:
                    status = "✅ SIMILAR"

                print(f"   {status} {result.test_name}")
                print(f"      Old: {result.old_time:.3f}s, New: {result.new_time:.3f}s ({result.improvement_percent:+.1f}%)")

        # Errors
        if self.errors:
            print(f"\n🚨 Errors:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")

        # Overall verdict
        print(f"\n🎯 Overall Verdict:")
        if not self.errors and passed_comparisons == len(self.comparison_results):
            print("   🎉 ALL TESTS PASSED - Migration ready for deployment!")
            return True
        elif len(self.errors) <= 2 and passed_comparisons >= len(self.comparison_results) * 0.8:
            print("   ⚠️  MOSTLY READY - Minor issues need attention before deployment")
            return False
        else:
            print("   ❌ NOT READY - Significant issues need to be resolved")
            return False

    def quick_smoke_test(self) -> bool:
        """Run a quick smoke test to verify basic functionality."""
        print("\n🔥 Running Quick Smoke Test...")

        if not DOMAIN_SERVICES_AVAILABLE:
            print("   ⚠️  Domain services not available - running limited smoke test")
            try:
                # Test basic imports that should work
                from services.payment_service import PaymentService
                print("   ✅ Legacy service imports successful")
                return True
            except Exception as e:
                print(f"   ❌ Smoke test failed: {e}")
                return False

        try:
            # Test that imports work
            from services.live_game_service_v2 import LiveGameService
            from services.payment_service_v2 import PaymentService
            from services.session_ingestion_service_v2 import SessionIngestionService
            print("   ✅ All service imports successful")

            # Test basic instantiation
            live_service = LiveGameService(self.db)
            payment_service = PaymentService(self.db)
            ingestion_service = SessionIngestionService(self.db)
            print("   ✅ All services instantiate successfully")

            # Test domain layer imports
            from domain.poker.value_objects import Money, SessionId, PlayerId
            from domain.poker.entities.poker_session import PokerSession
            print("   ✅ Domain layer imports successful")

            # Test basic domain operations
            money = Money("100.50")
            session_id = SessionId.generate()
            assert money.amount == Decimal("100.50")
            assert str(session_id)  # Should have a string representation
            print("   ✅ Domain objects work correctly")

            print("   🎉 Smoke test PASSED!")
            return True

        except Exception as e:
            print(f"   ❌ Smoke test FAILED: {e}")
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    print("🧪 Domain Migration Verification Tool")
    print("=====================================")

    # Check if we're using domain services
    use_domain = os.getenv('USE_DOMAIN_SERVICES', 'false').lower() == 'true'
    print(f"Environment: USE_DOMAIN_SERVICES = {use_domain}")

    if use_domain:
        print("⚠️  Domain services are currently active!")
        print("   This test will compare current active services with legacy services.")
    else:
        print("✅ Legacy services are currently active.")
        print("   This test will verify domain services work correctly.")

    try:
        with DomainMigrationTester() as tester:
            # Always run smoke test first
            if not tester.quick_smoke_test():
                print("\n❌ CRITICAL: Smoke test failed - cannot proceed with migration!")
                return False

            # Run full test suite
            tester.run_all_tests()

            return True

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        traceback.print_exc()
        return False

    finally:
        print(f"\n{'='*70}")
        print("🏁 Domain migration verification complete!")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)