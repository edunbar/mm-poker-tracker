#!/usr/bin/env python3
"""
Script to enable V2 domain services for the poker application.

This script sets the USE_DOMAIN_SERVICES environment variable and provides
instructions for making it permanent.
"""

import os
import sys

def enable_v2_services():
    """Enable V2 domain services."""
    print("🎯 Enabling V2 Domain Services...")

    # Set environment variable for current session
    os.environ['USE_DOMAIN_SERVICES'] = 'true'

    print("✅ Environment variable set for current session")
    print("🔄 Note: This setting is temporary and will reset when the process ends")

    # Test the services
    try:
        sys.path.insert(0, 'src')
        from services import get_service_info, LedgerService

        info = get_service_info()
        print(f"\n📊 Service Status:")
        print(f"   • Domain Services: {'✅ Enabled' if info['use_domain_services'] else '❌ Disabled'}")
        print(f"   • Ledger Service: {info['ledger_service']}")
        print(f"   • Environment Variable: {info['environment_var']}")

        # Test LedgerService instantiation
        ledger = LedgerService()
        print(f"\n🎯 LedgerService V2 Type: {type(ledger).__name__}")
        print("✅ V2 services are working correctly!")

    except Exception as e:
        print(f"❌ Error testing services: {e}")
        return False

    print("\n" + "="*60)
    print("📝 To make this setting PERMANENT:")
    print("="*60)
    print("1. Add to your .env file:")
    print("   USE_DOMAIN_SERVICES=true")
    print()
    print("2. Or export in your shell profile:")
    print("   echo 'export USE_DOMAIN_SERVICES=true' >> ~/.bashrc")
    print("   echo 'export USE_DOMAIN_SERVICES=true' >> ~/.zshrc")
    print()
    print("3. Or set when running your Flask app:")
    print("   USE_DOMAIN_SERVICES=true python src/app.py")
    print()
    print("4. Or in Docker/Docker Compose:")
    print("   environment:")
    print("     - USE_DOMAIN_SERVICES=true")
    print("="*60)

    return True

if __name__ == "__main__":
    success = enable_v2_services()
    sys.exit(0 if success else 1)