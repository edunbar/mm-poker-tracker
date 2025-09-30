#!/usr/bin/env python3
"""
Quick script to check which service versions are currently loaded.
"""

import sys
import os
from dotenv import load_dotenv

def check_service_status():
    """Check current service status."""
    print("🔍 Checking Service Status...")
    print("="*50)

    # Load environment variables
    load_dotenv()
    env_var = os.getenv('USE_DOMAIN_SERVICES', 'not_set')
    print(f"📄 .env file USE_DOMAIN_SERVICES: {env_var}")

    # Check services
    try:
        sys.path.insert(0, 'src')
        from services import get_service_info, LedgerService

        info = get_service_info()

        print(f"\n📊 Current Service Configuration:")
        print(f"   🎯 Domain Services: {'✅ ENABLED' if info['use_domain_services'] else '❌ DISABLED'}")
        print(f"   📝 Ledger Service: {info['ledger_service'].upper()}")
        print(f"   🔧 Live Game Service: {info['live_game_service']}")
        print(f"   💳 Payment Service: {info['payment_service']}")
        print(f"   📊 Game Summary Service: {info['game_summary_service']}")
        print(f"   📥 Session Ingestion Service: {info['session_ingestion_service']}")

        # Test LedgerService
        ledger = LedgerService()
        service_module = ledger.__class__.__module__

        print(f"\n🎯 LedgerService Details:")
        print(f"   Module: {service_module}")
        print(f"   Type: {type(ledger).__name__}")
        print(f"   Version: {'V2 (Domain)' if 'v2' in service_module else 'V1 (Legacy)'}")

        # Available methods
        methods = [m for m in dir(ledger) if not m.startswith('_')]
        print(f"   Methods: {', '.join(methods)}")

        # Test GameSummaryService
        from services import GameSummaryService
        summary_service = GameSummaryService()
        summary_module = summary_service.__class__.__module__

        print(f"\n📊 GameSummaryService Details:")
        print(f"   Module: {summary_module}")
        print(f"   Type: {type(summary_service).__name__}")
        print(f"   Version: {'V2 (Domain)' if 'v2' in summary_module else 'V1 (Legacy)'}")

        # Test direct imports used by routes
        from services.game_summary_service_v2 import get_player_summaries
        print(f"\n📋 Route Imports:")
        print(f"   get_player_summaries from: {get_player_summaries.__module__}")
        print(f"   Direct V2 import: {'✅ YES' if 'v2' in get_player_summaries.__module__ else '❌ NO'}")

        print(f"\n✅ All services loaded successfully!")

        if info['use_domain_services']:
            print(f"\n🎯 V2 SERVICES ARE ACTIVE!")
            print(f"   • Ledger page: Using domain services")
            print(f"   • Summary page: Using domain services")
            print(f"   • Routes: Direct V2 imports")
        else:
            print(f"\n⚠️  V1 services are active. To enable V2, set USE_DOMAIN_SERVICES=true")

    except Exception as e:
        print(f"❌ Error checking services: {e}")
        return False

    print("="*50)
    return True

if __name__ == "__main__":
    success = check_service_status()
    sys.exit(0 if success else 1)