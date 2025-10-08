"""
Test script for payment methods API endpoints.
This creates test data and verifies the corrected API routes work.
"""
import requests
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid

BASE_URL = "http://localhost:8000/api/games"

def setup_test_data():
    """Create test game and player in database."""
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        user="pokeruser",
        password="supersecret",
        database="poker_analytics"
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Create test game
    game_id = str(uuid.uuid4())
    public_code = "TEST01"
    admin_code = "ADMIN01"

    cursor.execute("""
        INSERT INTO games (id, public_code, admin_code, created_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (public_code) DO UPDATE SET admin_code = EXCLUDED.admin_code
        RETURNING id, public_code
    """, (game_id, public_code, admin_code))

    game = cursor.fetchone()
    print(f"✓ Created/found game: {game['public_code']} (ID: {game['id']})")

    # Create test player
    player_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO players (id, external_id, display_name, created_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (external_id) DO UPDATE SET display_name = EXCLUDED.display_name
        RETURNING id, display_name
    """, (player_id, "test_player_ext_001", "Test Player"))

    player = cursor.fetchone()
    print(f"✓ Created/found player: {player['display_name']} (ID: {player['id']})")

    # Link player to game
    cursor.execute("""
        INSERT INTO game_players (game_id, player_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (game['id'], player['id']))

    conn.commit()
    cursor.close()
    conn.close()

    return game['public_code'], str(player['id'])

def test_get_all_payment_methods(public_code):
    """Test GET /api/games/<public_code>/all-payment-methods"""
    url = f"{BASE_URL}/{public_code}/all-payment-methods"
    response = requests.get(url)
    print(f"\n1. GET {url}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_add_payment_method(player_id):
    """Test POST /api/games/players/<player_id>/payment-methods"""
    url = f"{BASE_URL}/players/{player_id}/payment-methods"
    data = {
        "payment_method": "Venmo",
        "payment_address": "testuser",  # Should auto-add @
        "is_primary": True
    }
    response = requests.post(url, json=data)
    print(f"\n2. POST {url}")
    print(f"   Data: {json.dumps(data, indent=2)}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 201:
        return response.json()['id']
    return None

def test_update_payment_method(player_id, method_id):
    """Test PUT /api/games/players/<player_id>/payment-methods/<method_id>"""
    url = f"{BASE_URL}/players/{player_id}/payment-methods/{method_id}"
    data = {
        "payment_address": "@updated_venmo_handle"
    }
    response = requests.put(url, json=data)
    print(f"\n3. PUT {url}")
    print(f"   Data: {json.dumps(data, indent=2)}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_add_second_method(player_id):
    """Test adding a second payment method (not primary)"""
    url = f"{BASE_URL}/players/{player_id}/payment-methods"
    data = {
        "payment_method": "Zelle",
        "payment_address": "555-1234",
        "is_primary": False
    }
    response = requests.post(url, json=data)
    print(f"\n4. POST {url} (add second method)")
    print(f"   Data: {json.dumps(data, indent=2)}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 201:
        return response.json()['id']
    return None

def test_set_primary(player_id, method_id):
    """Test POST /api/games/players/<player_id>/payment-methods/<method_id>/set-primary"""
    url = f"{BASE_URL}/players/{player_id}/payment-methods/{method_id}/set-primary"
    response = requests.post(url)
    print(f"\n5. POST {url}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_delete_payment_method(player_id, method_id):
    """Test DELETE /api/games/players/<player_id>/payment-methods/<method_id>"""
    url = f"{BASE_URL}/players/{player_id}/payment-methods/{method_id}"
    response = requests.delete(url)
    print(f"\n6. DELETE {url}")
    print(f"   Status: {response.status_code}")
    return response.status_code == 204

def main():
    print("=" * 70)
    print("TESTING PAYMENT METHODS API")
    print("=" * 70)

    # Setup
    public_code, player_id = setup_test_data()

    # Test 1: Get all payment methods (should be empty initially)
    test_get_all_payment_methods(public_code)

    # Test 2: Add first payment method (Venmo, primary)
    method1_id = test_add_payment_method(player_id)
    if not method1_id:
        print("❌ Failed to add first payment method")
        return

    # Test 3: Update payment method
    test_update_payment_method(player_id, method1_id)

    # Test 4: Add second payment method (Zelle, not primary)
    method2_id = test_add_second_method(player_id)
    if not method2_id:
        print("❌ Failed to add second payment method")
        return

    # Test 5: Set second method as primary (should unset first)
    test_set_primary(player_id, method2_id)

    # Test 6: Get all payment methods (should show both, with Zelle as primary)
    test_get_all_payment_methods(public_code)

    # Test 7: Delete first method
    test_delete_payment_method(player_id, method1_id)

    # Final check
    test_get_all_payment_methods(public_code)

    print("\n" + "=" * 70)
    print("✓ ALL TESTS COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    main()
