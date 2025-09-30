"""
Service selection based on environment variable.

Simple service switcher that allows toggling between legacy and domain-based services
without complex feature flags or code changes in the routes.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Check environment variable for service selection
USE_DOMAIN_SERVICES = os.getenv('USE_DOMAIN_SERVICES', 'false').lower() == 'true'

# Service selection and imports
if USE_DOMAIN_SERVICES:
    try:
        from .live_game_service_v2 import LiveGameService
        from .session_ingestion_service_v2 import SessionIngestionService, ingest_session
        from .payment_service_v2 import PaymentService
        from .game_summary_service_v2 import GameSummaryService
        from .ledger_service_v2 import LedgerService

        logger.info("🎯 Using DOMAIN-BASED services")
        print("🎯 Using DOMAIN-BASED services")

    except ImportError as e:
        logger.error(f"❌ Failed to import domain-based services: {e}")
        print(f"❌ Failed to import domain-based services: {e}")
        print("   Falling back to legacy services...")

        # Fallback to legacy services
        from .payment_service import PaymentService
        from .session_ingestion_service import ingest_session
        from .game_summary_service import GameSummaryService

        # Legacy ledger_service.py contains functions, not a class
        # Create a wrapper class for compatibility
        import services.ledger_service as legacy_ledger

        class LedgerService:
            """Wrapper for legacy ledger service functions."""

            def __init__(self, db_session=None):
                self._db_session = db_session

            def get_all_session_summaries(self, public_code: str):
                return legacy_ledger.get_all_session_summaries(public_code)

            def get_session_summary(self, session_id: str, player_id: str):
                return legacy_ledger.get_session_summary(session_id, player_id)

            def update_session_summary(self, session_id: str, player_id: str, updates: dict):
                return legacy_ledger.update_session_summary(session_id, player_id, updates)

            def delete_session_summary(self, session_id: str, player_id: str):
                return legacy_ledger.delete_session_summary(session_id, player_id)

            def delete_entire_session(self, session_id: str):
                return legacy_ledger.delete_entire_session(session_id)

        # Note: Legacy live_game_service.py contains utility functions, not a class
        # So we provide a wrapper to maintain compatibility
        class LiveGameService:
            """Wrapper for legacy live game functions."""

            def __init__(self, db_session=None):
                logger.warning("Using legacy LiveGameService wrapper - limited functionality")
                self._db_session = db_session

            def end_session(self, session_id: str, cash_out_amount: float):
                raise NotImplementedError("Legacy live game service doesn't have end_session method")

        logger.warning("⚠️  Using LEGACY services (domain import failed)")
        print("⚠️  Using LEGACY services (domain import failed)")

else:
    # Use legacy services
    from .payment_service import PaymentService
    from .session_ingestion_service import ingest_session
    from .game_summary_service import GameSummaryService

    # Legacy ledger_service.py contains functions, not a class
    # Create a wrapper class for compatibility
    import services.ledger_service as legacy_ledger

    class LedgerService:
        """Wrapper for legacy ledger service functions."""

        def __init__(self, db_session=None):
            self._db_session = db_session

        def get_all_session_summaries(self, public_code: str):
            return legacy_ledger.get_all_session_summaries(public_code)

        def get_session_summary(self, session_id: str, player_id: str):
            return legacy_ledger.get_session_summary(session_id, player_id)

        def update_session_summary(self, session_id: str, player_id: str, updates: dict):
            return legacy_ledger.update_session_summary(session_id, player_id, updates)

        def delete_session_summary(self, session_id: str, player_id: str):
            return legacy_ledger.delete_session_summary(session_id, player_id)

        def delete_entire_session(self, session_id: str):
            return legacy_ledger.delete_entire_session(session_id)

    # Legacy live_game_service.py contains utility functions, not a class
    # Create a minimal wrapper for compatibility
    class LiveGameService:
        """Wrapper for legacy live game functions."""

        def __init__(self, db_session=None):
            self._db_session = db_session

        def end_session(self, session_id: str, cash_out_amount: float):
            raise NotImplementedError(
                "Legacy live game service doesn't have end_session method. "
                "Set USE_DOMAIN_SERVICES=true to use domain-based LiveGameService."
            )

    logger.info("🔧 Using LEGACY services")
    print("🔧 Using LEGACY services")

# Additional service imports that don't have domain versions yet
# These will continue to use legacy implementations
# Temporarily commenting out problematic imports for migration testing
# from .audit_service import AuditService
# from .game_creation_service import GameCreationService
# from .ledger_service import LedgerService
# from .transaction_service import TransactionService
# from .player_verification_service import PlayerVerificationService
from .poker_statistics_service import PokerStatisticsProcessor

# Export all services for easy importing
__all__ = [
    # Core services (can be domain or legacy based)
    'LiveGameService',
    'PaymentService',
    'SessionIngestionService',
    'ingest_session',
    'GameSummaryService',
    'LedgerService',

    # Legacy services (not yet migrated to domain)
    # Temporarily commented out for migration testing:
    # 'AuditService',
    # 'GameCreationService',
    # 'LedgerService',
    # 'TransactionService',
    # 'PlayerVerificationService',
    'PokerStatisticsProcessor',
]


def get_service_info() -> dict:
    """
    Get information about currently loaded services.

    Useful for debugging and monitoring which services are active.
    """
    return {
        'use_domain_services': USE_DOMAIN_SERVICES,
        'live_game_service': 'domain' if USE_DOMAIN_SERVICES else 'legacy',
        'payment_service': 'domain' if USE_DOMAIN_SERVICES else 'legacy',
        'session_ingestion_service': 'domain' if USE_DOMAIN_SERVICES else 'legacy',
        'game_summary_service': 'domain' if USE_DOMAIN_SERVICES else 'legacy',
        'ledger_service': 'domain' if USE_DOMAIN_SERVICES else 'legacy',
        'environment_var': os.getenv('USE_DOMAIN_SERVICES', 'not_set'),
    }


def switch_to_domain_services() -> bool:
    """
    Programmatically switch to domain services.

    Note: This requires a server restart to take effect since imports are cached.

    Returns:
        True if switch was successful, False otherwise
    """
    os.environ['USE_DOMAIN_SERVICES'] = 'true'
    logger.info("🔄 Environment variable set to use domain services - restart required")
    return True


def switch_to_legacy_services() -> bool:
    """
    Programmatically switch to legacy services.

    Note: This requires a server restart to take effect since imports are cached.

    Returns:
        True if switch was successful, False otherwise
    """
    os.environ['USE_DOMAIN_SERVICES'] = 'false'
    logger.info("🔄 Environment variable set to use legacy services - restart required")
    return True


def validate_service_compatibility() -> dict:
    """
    Validate that the currently loaded services are compatible.

    Returns:
        Dictionary with validation results
    """
    results = {
        'valid': True,
        'issues': [],
        'service_info': get_service_info()
    }

    try:
        # Test service instantiation
        payment_service = PaymentService()
        live_service = LiveGameService()
        ledger_service = LedgerService()

        # Check for required methods
        if not hasattr(payment_service, 'record_payment'):
            results['issues'].append("PaymentService missing record_payment method")
            results['valid'] = False

        if not hasattr(payment_service, 'get_payment_summary'):
            results['issues'].append("PaymentService missing get_payment_summary method")
            results['valid'] = False

        if not hasattr(live_service, 'end_session'):
            # This is expected for legacy service, so just note it
            results['issues'].append("LiveGameService missing end_session method (expected for legacy)")

        # Check LedgerService methods
        if hasattr(ledger_service, 'get_all_session_summaries'):
            # Domain version - check for class methods
            if not hasattr(ledger_service, 'update_session_summary'):
                results['issues'].append("LedgerService missing update_session_summary method")
                results['valid'] = False
        else:
            # Legacy version - this is expected
            results['issues'].append("LedgerService is legacy version (functions, not class methods)")

    except Exception as e:
        results['issues'].append(f"Service instantiation failed: {e}")
        results['valid'] = False

    return results


# Log service selection at import time
service_info = get_service_info()
logger.info(f"Services loaded: {service_info}")

# Validate services on import
validation = validate_service_compatibility()
if not validation['valid']:
    logger.warning(f"Service compatibility issues detected: {validation['issues']}")
    for issue in validation['issues']:
        print(f"⚠️  {issue}")
else:
    logger.debug("All services loaded successfully")


# Context manager for temporary service switching (for testing)
class TemporaryServiceSwitch:
    """Context manager for temporarily switching services during testing."""

    def __init__(self, use_domain: bool):
        self.use_domain = use_domain
        self.original_value = os.getenv('USE_DOMAIN_SERVICES')

    def __enter__(self):
        os.environ['USE_DOMAIN_SERVICES'] = 'true' if self.use_domain else 'false'
        logger.info(f"Temporarily switched to {'domain' if self.use_domain else 'legacy'} services")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_value is not None:
            os.environ['USE_DOMAIN_SERVICES'] = self.original_value
        else:
            os.environ.pop('USE_DOMAIN_SERVICES', None)
        logger.info("Restored original service configuration")