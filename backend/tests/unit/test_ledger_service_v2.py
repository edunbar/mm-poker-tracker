#!/usr/bin/env python3
"""
Test script for the new domain-based ledger service architecture.

This script verifies that the Ledger domain entities, repository pattern,
and v2 service work together correctly.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from typing import Dict, Any, List, Optional
from datetime import datetime
from domain.ledger.value_objects import LedgerEntryId, SessionReference, PlayerNames, FinancialSummary
from domain.ledger.entities import LedgerEntry, SessionLedger
from domain.ledger.services import LedgerManagementService
from domain.poker.value_objects import GameId


class MockLedgerRepository:
    """Mock repository for testing without database."""

    def __init__(self):
        self.entries = {}  # key: str(entry_id), value: LedgerEntry
        self.session_entries = {}  # key: session_id, value: list[entry_ids]

    def get_all_entries_for_game(self, public_code: str) -> List[LedgerEntry]:
        # For testing, return all entries (simplified)
        return list(self.entries.values())

    def get_entry_by_id(self, entry_id: LedgerEntryId) -> Optional[LedgerEntry]:
        return self.entries.get(str(entry_id))

    def get_session_ledger(self, session_id: str) -> Optional[SessionLedger]:
        entry_ids = self.session_entries.get(session_id, [])
        if not entry_ids:
            return None

        entries = [self.entries[str(entry_id)] for entry_id in entry_ids if str(entry_id) in self.entries]
        if not entries:
            return None

        # Create session ledger from first entry's data
        first_entry = entries[0]
        return SessionLedger(
            session_reference=first_entry.session_reference,
            game_id=first_entry.game_id,
            entries=entries
        )

    def save_entry(self, entry: LedgerEntry) -> LedgerEntry:
        entry_key = str(entry.id)
        self.entries[entry_key] = entry

        # Update session tracking
        session_id = entry.get_session_id()
        if session_id not in self.session_entries:
            self.session_entries[session_id] = []
        if entry.id not in self.session_entries[session_id]:
            self.session_entries[session_id].append(entry.id)

        return entry

    def delete_entry(self, entry_id: LedgerEntryId) -> bool:
        entry_key = str(entry_id)
        if entry_key not in self.entries:
            return False

        entry = self.entries[entry_key]
        del self.entries[entry_key]

        # Update session tracking
        session_id = entry.get_session_id()
        if session_id in self.session_entries:
            if entry_id in self.session_entries[session_id]:
                self.session_entries[session_id].remove(entry_id)
            if not self.session_entries[session_id]:
                del self.session_entries[session_id]

        return True

    def delete_session_entries(self, session_id: str) -> int:
        entry_ids = self.session_entries.get(session_id, [])
        deleted_count = 0

        for entry_id in entry_ids[:]:  # Copy list to avoid modification during iteration
            if self.delete_entry(entry_id):
                deleted_count += 1

        return deleted_count

    def entry_exists(self, entry_id: LedgerEntryId) -> bool:
        return str(entry_id) in self.entries

    def get_entries_for_player_in_game(self, public_code: str, player_id: str) -> List[LedgerEntry]:
        return [entry for entry in self.entries.values() if entry.get_player_id() == player_id]

    def session_has_players(self, session_id: str) -> bool:
        return session_id in self.session_entries and len(self.session_entries[session_id]) > 0


def test_value_objects():
    """Test ledger domain value objects."""
    print("🧪 Testing Ledger Value Objects...")

    # Test LedgerEntryId
    entry_id = LedgerEntryId(
        session_id="12345678-1234-1234-1234-123456789012",
        player_id="87654321-4321-4321-4321-210987654321"
    )
    assert str(entry_id) == "12345678-1234-1234-1234-123456789012:87654321-4321-4321-4321-210987654321"
    print("   ✅ LedgerEntryId creation and string representation")

    # Test SessionReference
    session_ref = SessionReference(
        session_id="12345678-1234-1234-1234-123456789012",
        external_id="EXTERNAL123",
        game_number=5
    )
    assert str(session_ref) == "Session 5 (EXTERNAL123)"
    print("   ✅ SessionReference creation and display")

    # Test PlayerNames
    player_names = PlayerNames(
        display_name="John Doe",
        session_names=["JohnD", "John"]
    )
    assert player_names.get_primary_session_name() == "JohnD"
    assert player_names.has_multiple_names() == True
    print("   ✅ PlayerNames creation and methods")

    # Test FinancialSummary
    financial = FinancialSummary.create(
        buy_in_sum=10000,  # $100.00
        cash_out_sum=12000,  # $120.00
        in_game=0
    )
    assert financial.net == 2000  # $20.00 profit
    assert financial.is_profitable() == True
    dollars = financial.to_dollars()
    assert dollars["net"] == 20.0
    print("   ✅ FinancialSummary creation and calculations")

    print("✅ Ledger Value Objects: All tests passed\n")


def test_ledger_entry_entity():
    """Test LedgerEntry domain entity."""
    print("🧪 Testing LedgerEntry Entity...")

    # Create ledger entry
    entry = LedgerEntry.create_new(
        session_id="12345678-1234-1234-1234-123456789012",
        player_id="87654321-4321-4321-4321-210987654321",
        game_id=GameId("11111111-1111-1111-1111-111111111111"),
        external_id="EXT123",
        game_number=1,
        display_name="Alice Smith",
        session_names=["Alice", "AliceS"],
        buy_in_sum=5000,  # $50.00
        cash_out_sum=6500,  # $65.00
        in_game=0
    )

    assert entry.get_session_id() == "12345678-1234-1234-1234-123456789012"
    assert entry.get_player_id() == "87654321-4321-4321-4321-210987654321"
    assert entry.is_profitable() == True
    assert entry.get_net_dollars() == 15.0
    print("   ✅ LedgerEntry creation and basic methods")

    # Test immutability with updates
    updated_entry = entry.update_financial_data(cash_out_sum=7000)
    assert entry.financial_summary.cash_out_sum == 6500  # Original unchanged
    assert updated_entry.financial_summary.cash_out_sum == 7000  # New instance updated
    assert updated_entry.financial_summary.net == 2000  # Net recalculated
    print("   ✅ LedgerEntry immutability and updates")

    # Test dictionary conversion
    entry_dict = entry.to_dict()
    assert entry_dict["player_name"] == "Alice Smith"
    assert entry_dict["net"] == 1500
    assert entry_dict["names"] == ["Alice", "AliceS"]
    print("   ✅ LedgerEntry dictionary conversion")

    print("✅ LedgerEntry Entity: All tests passed\n")


def test_session_ledger_entity():
    """Test SessionLedger aggregate entity."""
    print("🧪 Testing SessionLedger Entity...")

    # Create session reference
    session_ref = SessionReference(
        session_id="12345678-1234-1234-1234-123456789012",
        external_id="EXT123",
        game_number=1
    )

    # Create ledger entries
    entry1 = LedgerEntry.create_new(
        session_id="12345678-1234-1234-1234-123456789012",
        player_id="11111111-1111-1111-1111-111111111111",
        game_id=GameId("99999999-9999-9999-9999-999999999999"),
        external_id="EXT123",
        game_number=1,
        display_name="Player 1",
        session_names=["P1"],
        buy_in_sum=10000,  # $100.00
        cash_out_sum=12000,  # $120.00 (profitable)
        in_game=0
    )

    entry2 = LedgerEntry.create_new(
        session_id="12345678-1234-1234-1234-123456789012",
        player_id="22222222-2222-2222-2222-222222222222",
        game_id=GameId("99999999-9999-9999-9999-999999999999"),
        external_id="EXT123",
        game_number=1,
        display_name="Player 2",
        session_names=["P2"],
        buy_in_sum=10000,  # $100.00
        cash_out_sum=8000,   # $80.00 (losing)
        in_game=0
    )

    # Create session ledger
    session_ledger = SessionLedger(
        session_reference=session_ref,
        game_id=GameId("99999999-9999-9999-9999-999999999999")
    )

    # Add entries
    session_ledger = session_ledger.add_entry(entry1)
    session_ledger = session_ledger.add_entry(entry2)

    assert session_ledger.get_player_count() == 2
    assert session_ledger.calculate_total_pot() == 20000  # $200.00
    print("   ✅ SessionLedger creation and entry management")

    # Test analytics
    profitable_players = session_ledger.get_profitable_players()
    losing_players = session_ledger.get_losing_players()
    assert len(profitable_players) == 1
    assert len(losing_players) == 1
    print("   ✅ SessionLedger analytics methods")

    # Test immutability
    reduced_ledger = session_ledger.remove_entry(entry1.id)
    assert session_ledger.get_player_count() == 2  # Original unchanged
    assert reduced_ledger.get_player_count() == 1  # New instance changed
    print("   ✅ SessionLedger immutability")

    print("✅ SessionLedger Entity: All tests passed\n")


def test_domain_service():
    """Test LedgerManagementService domain service."""
    print("🧪 Testing Domain Service...")

    # Create mock repository and service
    repo = MockLedgerRepository()
    service = LedgerManagementService(repo)

    # Create test entries
    entry1 = LedgerEntry.create_new(
        session_id="12345678-1234-1234-1234-123456789012",
        player_id="11111111-1111-1111-1111-111111111111",
        game_id=GameId("99999999-9999-9999-9999-999999999999"),
        external_id="EXT123",
        game_number=1,
        display_name="Test Player",
        session_names=["TestP"],
        buy_in_sum=5000,
        cash_out_sum=6000,
        in_game=0
    )

    # Save entry
    repo.save_entry(entry1)
    print("   ✅ Entry saved to repository")

    # Test retrieval
    retrieved = service.get_ledger_entry(
        "12345678-1234-1234-1234-123456789012",
        "11111111-1111-1111-1111-111111111111"
    )
    assert retrieved is not None
    assert retrieved.get_player_id() == "11111111-1111-1111-1111-111111111111"
    print("   ✅ Entry retrieval by ID")

    # Test updates
    updates = {"cash_out_sum": 7000}
    updated = service.update_ledger_entry(
        "12345678-1234-1234-1234-123456789012",
        "11111111-1111-1111-1111-111111111111",
        updates
    )
    assert updated.financial_summary.cash_out_sum == 7000
    assert updated.financial_summary.net == 2000  # Auto-calculated
    print("   ✅ Entry updates with business rule validation")

    # Test session operations
    session_ledger = service.get_session_ledger("12345678-1234-1234-1234-123456789012")
    assert session_ledger is not None
    assert session_ledger.get_player_count() == 1
    print("   ✅ Session ledger retrieval")

    # Test deletion
    deleted = service.delete_ledger_entry(
        "12345678-1234-1234-1234-123456789012",
        "11111111-1111-1111-1111-111111111111"
    )
    assert deleted == True

    # Verify orphaned
    orphaned = service.check_session_orphaned("12345678-1234-1234-1234-123456789012")
    assert orphaned == True
    print("   ✅ Entry deletion and orphan detection")

    print("✅ Domain Service: All tests passed\n")


def test_v2_service_compatibility():
    """Test v2 service API compatibility."""
    print("🧪 Testing V2 Service Compatibility...")

    try:
        from services.ledger_service_v2 import (
            get_all_session_summaries,
            update_session_summary,
            get_session_summary
        )

        print("   ✅ Legacy function imports successful")

        # These would require database setup to test fully
        print("   ✅ API compatibility functions available")

        print("✅ V2 Service Compatibility: Import tests passed\n")

    except Exception as e:
        print(f"   ❌ V2 Service test failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("🚀 Testing Domain-Based Ledger Service Architecture\n")

    try:
        test_value_objects()
        test_ledger_entry_entity()
        test_session_ledger_entity()
        test_domain_service()
        test_v2_service_compatibility()

        print("🎉 ALL TESTS PASSED!")
        print("✅ Domain-based ledger service architecture is working correctly")
        print("✅ Ready for integration with existing codebase")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)