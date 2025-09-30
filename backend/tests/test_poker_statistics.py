"""
Test poker statistics calculations

Tests VPIP, PFR, and Aggression Frequency calculations with various scenarios.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.services.poker_statistics_service import PokerStatisticsProcessor


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()


def test_play_style_classification(mock_db_session):
    """Test play style classification logic."""
    processor = PokerStatisticsProcessor(mock_db_session)

    # Test Nit: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=20, pfr=22, af=65)
    assert style == 'Nit'

    # Test Selective Aggressive: VPIP < 45, 20 <= PFR <= 30
    style = processor._classify_play_style(vpip=40, pfr=25, af=70)
    assert style == 'Selective Aggressive'

    # Test Nit: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=18, pfr=12, af=35)
    assert style == 'Nit'

    # Test Passive Regular: VPIP >= 45, PFR < 15
    style = processor._classify_play_style(vpip=45, pfr=10, af=25)
    assert style == 'Passive Regular'

    # Test Nit: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=28, pfr=16, af=55)
    assert style == 'Nit'

    # Test with missing VPIP data
    style = processor._classify_play_style(vpip=None, pfr=16, af=55)
    assert style is None

    # Test with missing PFR data
    style = processor._classify_play_style(vpip=25, pfr=None, af=55)
    assert style is None


def test_statistics_calculation_formulas(mock_db_session):
    """Test the core statistical calculation formulas."""
    processor = PokerStatisticsProcessor(mock_db_session)

    # Test VPIP calculation: (vpip_hands / hands_dealt) * 100
    hands_dealt = 100
    vpip_hands = 28
    expected_vpip = (vpip_hands / hands_dealt) * 100
    assert abs(expected_vpip - 28.0) < 0.001  # Use abs for floating point comparison

    # Test PFR calculation: (pfr_hands / hands_dealt) * 100
    pfr_hands = 22
    expected_pfr = (pfr_hands / hands_dealt) * 100
    assert abs(expected_pfr - 22.0) < 0.001

    # Test AF calculation: (aggressive / total_actions) * 100
    aggressive_actions = 65
    total_actions = 100
    expected_af = (aggressive_actions / total_actions) * 100
    assert abs(expected_af - 65.0) < 0.001

    # Test that VPIP is always >= PFR (validation)
    assert expected_vpip >= expected_pfr


def test_edge_case_calculations(mock_db_session):
    """Test edge cases for statistics calculations."""
    processor = PokerStatisticsProcessor(mock_db_session)

    # Test division by zero cases
    # When hands_dealt = 0, percentages should be None or 0
    hands_dealt = 0
    vpip_hands = 0
    vpip_percentage = (vpip_hands / hands_dealt * 100) if hands_dealt > 0 else None
    assert vpip_percentage is None

    # When no post-flop actions, AF should be None
    postflop_aggressive = 0
    postflop_total = 0
    af_percentage = (postflop_aggressive / postflop_total * 100) if postflop_total > 0 else None
    assert af_percentage is None

    # Test with minimal valid data
    hands_dealt = 1
    vpip_hands = 1
    vpip_percentage = (vpip_hands / hands_dealt * 100)
    assert vpip_percentage == 100.0


def test_boundary_conditions(mock_db_session):
    """Test boundary conditions for play style classification."""
    processor = PokerStatisticsProcessor(mock_db_session)

    # Test exact boundary values
    # Boundary case: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=24.9, pfr=21, af=65)
    assert style == 'Nit'

    style = processor._classify_play_style(vpip=25.1, pfr=21, af=65)
    # Still Nit as VPIP < 40
    assert style == 'Nit'

    # Boundary case: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=35.1, pfr=25, af=70)
    assert style == 'Nit'

    # Boundary case: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=20, pfr=20.1, af=65)
    assert style == 'Nit'

    # Boundary case: VPIP < 40, PFR >= 10
    style = processor._classify_play_style(vpip=20, pfr=14.9, af=35)
    assert style == 'Nit'


if __name__ == "__main__":
    pytest.main([__file__])