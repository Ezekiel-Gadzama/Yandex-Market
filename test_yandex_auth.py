"""
Test script to verify Yandex Market API authentication
Run with: docker-compose exec backend python test_yandex_auth.py
"""
import sys
sys.path.insert(0, '/app')

from app.services.yandex_api import YandexMarketAPI

def test_auth():
    print("Testing Yandex Market API Authentication...")
    print("=" * 60)
    
    try:
        api = YandexMarketAPI()
        print(f"✓ API initialized successfully")
        print(f"  Base URL: {api.base_url}")
        print(f"  Campaign ID: {api.campaign_id}")
        print(f"  Token (first 20 chars): {api.api_token[:20]}...")
        
        # Test authentication by getting products
        print("\nTesting GET /v2/campaigns/{id}/offer-mapping-entries...")
        products = api.get_products()
        print(f"✓ Successfully fetched products: {len(products)} found")
        
        # Test getting orders
        print("\nTesting GET /v2/campaigns/{id}/orders...")
        orders = api.get_orders()
        print(f"✓ Successfully fetched orders: {len(orders)} found")
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("Your Yandex Market API authentication is working correctly.")
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        print("\nPlease set your API credentials in:")
        print("  1. Settings page in the UI, OR")
        print("  2. Environment variables (YANDEX_MARKET_API_TOKEN, YANDEX_MARKET_CAMPAIGN_ID)")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ API Error: {e}")
        print("\nPossible causes:")
        print("  1. Invalid or expired API token")
        print("  2. Incorrect campaign ID")
        print("  3. API permissions not granted")
        print("\nCheck:")
        print("  - Yandex Market Partner Dashboard → Settings → API and Modules")
        print("  - Ensure token has required permissions")
        print("  - Verify campaign ID matches your store")
        sys.exit(1)

if __name__ == "__main__":
    test_auth()
