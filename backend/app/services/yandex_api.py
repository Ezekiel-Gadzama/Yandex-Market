import httpx
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse
from app.config import settings
from app import models
from app.database import SessionLocal


class YandexMarketAPI:
    """Service for interacting with Yandex Market Partner API"""
    
    def __init__(self):
        # Use .env first, then database if value exists in database
        # Start with .env values
        self.base_url = settings.YANDEX_MARKET_API_URL
        self.api_token = settings.YANDEX_MARKET_API_TOKEN
        # Strip whitespace from business_id and campaign_id if they're strings
        self.business_id = settings.YANDEX_BUSINESS_ID.strip() if isinstance(settings.YANDEX_BUSINESS_ID, str) else settings.YANDEX_BUSINESS_ID
        self.campaign_id = settings.YANDEX_MARKET_CAMPAIGN_ID.strip() if isinstance(settings.YANDEX_MARKET_CAMPAIGN_ID, str) else settings.YANDEX_MARKET_CAMPAIGN_ID
        
        # Override with database values if they exist (and are not empty)
        db = SessionLocal()
        try:
            app_settings = db.query(models.AppSettings).first()
            if app_settings:
                # Only use database value if it's not None/empty
                # This allows .env values to be used as fallback if database value is empty
                if app_settings.yandex_api_token and app_settings.yandex_api_token.strip():
                    self.api_token = app_settings.yandex_api_token
                if app_settings.yandex_business_id and app_settings.yandex_business_id.strip():
                    self.business_id = app_settings.yandex_business_id
                if app_settings.yandex_campaign_id and app_settings.yandex_campaign_id.strip():
                    self.campaign_id = app_settings.yandex_campaign_id
                if app_settings.yandex_api_url and app_settings.yandex_api_url.strip():
                    self.base_url = app_settings.yandex_api_url
        finally:
            db.close()
        
        if not self.api_token:
            raise ValueError("YANDEX_MARKET_API_TOKEN is required. Create a token in Yandex Market Partner dashboard.")
        
        # Detect token type: ACMA tokens work with Campaign API, OAuth tokens work with Business API
        self.is_acma_token = self.api_token.startswith("ACMA:")
        
        if self.is_acma_token:
            # ACMA tokens use Campaign API for products/orders - need campaign_id
            # But can also use Business API for reviews if business_id is provided
            if not self.campaign_id:
                raise ValueError("YANDEX_MARKET_CAMPAIGN_ID is required when using ACMA tokens. ACMA tokens work with Campaign API endpoints.")
            if self.business_id:
                print("ℹ️  Using ACMA token with Campaign API (campaign_id: {}) and Business API (business_id: {})".format(self.campaign_id, self.business_id))
            else:
                print("ℹ️  Using ACMA token with Campaign API (campaign_id: {}). Note: business_id is recommended for reviews access.".format(self.campaign_id))
        else:
            # OAuth tokens use Business API - need business_id
            if not self.business_id:
                raise ValueError("YANDEX_BUSINESS_ID is required when using OAuth tokens. OAuth tokens work with Business API endpoints.")
            print("ℹ️  Using OAuth token with Business API (business_id: {})".format(self.business_id))
    
    def _get_api_base_path(self) -> str:
        """Get the base API path based on token type"""
        if self.is_acma_token:
            # ACMA tokens use Campaign API
            return f"{self.base_url}/v2/campaigns/{self.campaign_id}"
        else:
            # OAuth tokens use Business API
            return f"{self.base_url}/v2/businesses/{self.business_id}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        # Yandex Market Partner API authentication
        # ACMA tokens use Api-Key header, OAuth tokens use Authorization header
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_token.startswith("ACMA:"):
            # ACMA application tokens use Api-Key header (not Authorization!)
            headers["Api-Key"] = self.api_token
        elif self.api_token.startswith("OAuth "):
            # Already has OAuth prefix
            headers["Authorization"] = self.api_token
        else:
            # Regular OAuth token - add OAuth prefix
            headers["Authorization"] = f"OAuth {self.api_token}"
        
        return headers
    
    def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with error logging"""
        try:
            with httpx.Client() as client:
                response = client.request(method, url, **kwargs)
                # Log error responses for debugging
                if response.status_code in [401, 403]:
                    print(f"Authentication error ({response.status_code}) for {method} {url}")
                    print(f"Response: {response.text}")
                    print(f"Headers sent: {kwargs.get('headers', {})}")
                elif not response.is_success:
                    print(f"Request failed ({response.status_code}) for {method} {url}")
                    print(f"Response: {response.text}")
                return response
        except httpx.HTTPError as e:
            print(f"HTTP error for {method} {url}: {str(e)}")
            raise
    
    def create_product(self, product: models.Product) -> Dict:
        """Create a product on Yandex Market using offer-mappings/update endpoint
        
        According to Yandex API documentation:
        - Business API: POST /v2/businesses/{businessId}/offer-mappings/update
        - Campaign API: POST /v2/campaigns/{campaignId}/offers/update
        """
        # Use correct API endpoint based on token type
        if self.is_acma_token:
            # Campaign API
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers/update"
        else:
            # Business API uses offer-mappings/update
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings/update"
        
        # Get data from yandex_full_data if available, otherwise use product fields
        yandex_data = product.yandex_full_data or {}
        
        # Extract images and videos from yandex_full_data
        images = yandex_data.get("pictures") or yandex_data.get("images") or []
        videos = yandex_data.get("videos") or []
        
        # If stored as JSON strings, parse them
        if isinstance(images, str):
            try:
                images = json.loads(images)
            except:
                images = []
        if isinstance(videos, str):
            try:
                videos = json.loads(videos)
            except:
                videos = []
        
        # Build offer payload - Business API format
        shop_sku = product.yandex_market_sku or yandex_data.get("offerId") or f"SKU-{product.id}"
        
        offer = {
            "shopSku": shop_sku,
            "name": product.name,
            "description": product.description or "",
            "price": {
                "value": product.selling_price,
                "currencyId": yandex_data.get("basicPrice", {}).get("currencyId") or "RUR"
            },
            "vat": yandex_data.get("vat") or product.vat_rate or "NOT_APPLICABLE",
            "availability": "ACTIVE" if product.is_active else "INACTIVE",
        }
        
        # Add parameterValues if available in yandex_full_data
        if "parameterValues" in yandex_data and isinstance(yandex_data["parameterValues"], list):
            offer["parameterValues"] = yandex_data["parameterValues"]
        
        # Add barcode if available
        if yandex_data.get("barcode") or product.barcode:
            barcode = yandex_data.get("barcode") or product.barcode
            offer["barcode"] = [barcode] if isinstance(barcode, str) else barcode
        
        # Add dimensions for physical products
        if yandex_data.get("dimensions"):
            offer["dimensions"] = yandex_data["dimensions"]
        elif product.width_cm or product.height_cm or product.length_cm or product.weight_kg:
            dimensions = {}
            if product.width_cm:
                dimensions["width"] = product.width_cm
            if product.height_cm:
                dimensions["height"] = product.height_cm
            if product.length_cm:
                dimensions["length"] = product.length_cm
            if product.weight_kg:
                dimensions["weight"] = product.weight_kg
            if dimensions:
                offer["dimensions"] = dimensions
        
        # Add oldPrice if available
        if yandex_data.get("oldPrice") or (product.crossed_out_price and product.crossed_out_price > product.selling_price):
            old_price = yandex_data.get("oldPrice") or product.crossed_out_price
            if old_price and old_price > product.selling_price:
                offer["oldPrice"] = {"value": old_price, "currencyId": "RUR"}
        
        # For digital products, use DBS model
        if product.product_type == models.ProductType.DIGITAL:
            offer["type"] = "DIGITAL"
            offer["model"] = yandex_data.get("model") or product.yandex_model or "DBS"
        else:
            offer["type"] = "PHYSICAL"
            if yandex_data.get("model") or product.yandex_model:
                offer["model"] = yandex_data.get("model") or product.yandex_model
        
        # Category information
        if yandex_data.get("mapping", {}).get("marketCategoryId"):
            offer["categoryId"] = yandex_data["mapping"]["marketCategoryId"]
        elif yandex_data.get("categoryId"):
            offer["categoryId"] = yandex_data["categoryId"]
        elif product.yandex_category_id:
            offer["categoryId"] = product.yandex_category_id
        
        # Images
        if images:
            offer["pictures"] = images
        
        # Videos
        if videos:
            offer["videos"] = videos
        
        # Build payload according to API
        if self.is_acma_token:
            # Campaign API expects {"offers": [offer]}
            payload = {"offers": [offer]}
        else:
            # Business API expects {"offerMappingEntries": [{"offer": {...}}]}
            payload = {
                "offerMappingEntries": [{
                    "offer": offer
                }]
            }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Return the created offer data
                if self.is_acma_token:
                    # Campaign API response format
                    return result
                else:
                    # Business API response format - extract offer from response
                    if "result" in result and "offerMappingEntries" in result["result"]:
                        entries = result["result"]["offerMappingEntries"]
                        if entries:
                            return entries[0].get("offer", {})
                    return result
        except httpx.HTTPError as e:
            error_msg = f"Failed to create product on Yandex Market: {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_msg += f" - Response: {e.response.text}"
            raise Exception(error_msg)
    
    def update_product(self, product: models.Product, field_updates: Dict = None) -> Dict:
        """Update a product on Yandex Market using yandex_full_data JSON"""
        if not product.yandex_market_id:
            raise ValueError("Product not synced with Yandex Market")
        
        if self.is_acma_token:
            # Campaign API: Use POST /v2/campaigns/*/offers/update or POST /v2/campaigns/*/offer-mapping-entries/updates
            # Based on endpoint list: POST /v2/campaigns/*/offers/update exists
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers/update"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings/update"
        
        # Get base data from yandex_full_data, merge with field_updates
        base_data = product.yandex_full_data or {}
        if field_updates:
            base_data = {**base_data, **field_updates}
        
        # Build offer payload from yandex_full_data
        # Use the structure that Yandex expects
        shop_sku = product.yandex_market_sku or base_data.get("offerId") or product.yandex_market_id
        
        # Get price - handle both object and number formats
        price_value = product.selling_price
        if base_data.get("basicPrice"):
            price_value = base_data["basicPrice"].get("value", price_value) if isinstance(base_data["basicPrice"], dict) else price_value
        elif base_data.get("price"):
            price_value = base_data["price"].get("value", price_value) if isinstance(base_data["price"], dict) else base_data["price"]
        
        currency_id = "RUR"
        if base_data.get("basicPrice", {}).get("currencyId"):
            currency_id = base_data["basicPrice"]["currencyId"]
        elif base_data.get("price", {}).get("currencyId"):
            currency_id = base_data["price"]["currencyId"]
        
        offer = {
            "shopSku": shop_sku,
            "name": base_data.get("name") or product.name,
            "description": base_data.get("description") or product.description or "",
            "price": {
                "value": price_value,
                "currencyId": currency_id
            },
            "vat": base_data.get("vat") or base_data.get("vat_rate") or "NOT_APPLICABLE",
            "availability": "ACTIVE" if product.is_active else "INACTIVE",
        }
        
        # Add parameterValues if available
        if "parameterValues" in base_data and isinstance(base_data["parameterValues"], list):
            offer["parameterValues"] = base_data["parameterValues"]
        
        # Add fields from yandex_full_data that Yandex expects
        if "barcode" in base_data:
            barcode = base_data["barcode"]
            offer["barcode"] = [barcode] if isinstance(barcode, str) else barcode
        
        if "dimensions" in base_data:
            offer["dimensions"] = base_data["dimensions"]
        elif any(key in base_data for key in ["width", "height", "length", "weight"]):
            dimensions = {}
            if "width" in base_data:
                dimensions["width"] = base_data["width"]
            if "height" in base_data:
                dimensions["height"] = base_data["height"]
            if "length" in base_data:
                dimensions["length"] = base_data["length"]
            if "weight" in base_data:
                dimensions["weight"] = base_data["weight"]
            if dimensions:
                offer["dimensions"] = dimensions
        
        if "oldPrice" in base_data or "crossed_out_price" in base_data:
            old_price = base_data.get("oldPrice")
            if isinstance(old_price, dict):
                old_price = old_price.get("value")
            elif not old_price:
                old_price = base_data.get("crossed_out_price")
            
            if old_price and old_price > price_value:
                offer["oldPrice"] = {"value": old_price, "currencyId": currency_id}
        
        if "model" in base_data:
            offer["model"] = base_data["model"]
        elif product.product_type == models.ProductType.DIGITAL:
            offer["model"] = "DBS"
        
        # Category from mapping or direct
        if base_data.get("mapping", {}).get("marketCategoryId"):
            offer["categoryId"] = base_data["mapping"]["marketCategoryId"]
        elif "categoryId" in base_data:
            offer["categoryId"] = base_data["categoryId"]
        elif "category" in base_data:
            offer["category"] = base_data["category"]
        
        # Extract params from yandex_full_data
        params = base_data.get("params", {})
        if not params:
            # Try to build params from individual fields in base_data
            if "vendor" in base_data or "brand" in base_data:
                params["vendor"] = base_data.get("vendor") or base_data.get("brand")
            if "platform" in base_data:
                params["platform"] = base_data["platform"]
            if "localization" in base_data:
                params["localization"] = base_data["localization"]
            if "publicationType" in base_data:
                params["publicationType"] = base_data["publicationType"]
            if "activationTerritory" in base_data:
                params["activationTerritory"] = base_data["activationTerritory"]
            if "edition" in base_data:
                params["edition"] = base_data["edition"]
            if "series" in base_data:
                params["series"] = base_data["series"]
            if "ageRestriction" in base_data:
                params["ageRestriction"] = base_data["ageRestriction"]
            if "hasActivationInstructions" in base_data:
                params["hasActivationInstructions"] = base_data["hasActivationInstructions"]
        
        # Images and videos from yandex_full_data
        if "pictures" in base_data:
            offer["pictures"] = base_data["pictures"]
        elif "images" in base_data:
            offer["pictures"] = base_data["images"]
        
        if "videos" in base_data:
            offer["videos"] = base_data["videos"]
        
        # Add params if any
        if params:
            offer["params"] = params
        
        if self.is_acma_token:
            # Campaign API: POST /v2/campaigns/*/offers/update expects offers array
            payload = {
                "offers": [offer]
            }
        else:
            # Business API expects {"offerMappingEntries": [{"offer": {...}}]}
            payload = {
                "offerMappingEntries": [{
                    "offer": offer
                }]
            }
        
        try:
            with httpx.Client() as client:
                # Both APIs use POST for updates
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update product on Yandex Market: {str(e)}")
    
    def get_products(self) -> List[Dict]:
        """Get all products from Yandex Market"""
        if self.is_acma_token:
            # Campaign API: Try POST /v2/campaigns/*/offers.json first (user's test code showed this works)
            # If that fails, try POST /v2/campaigns/*/offers (without .json)
            # Based on endpoint list: POST /v2/campaigns/*/offers exists
            urls_to_try = [
                f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers.json",
                f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers"
            ]
            payload = {
                "page": 1,
                "pageSize": 100
            }
            
            last_error = None
            for url in urls_to_try:
                try:
                    print(f"🔍 Fetching products from: {url}")
                    response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    print(f"✅ Received response from Yandex API")
                    
                    # Check response structure
                    if "offers" in data:
                        offers = data.get("offers", [])
                    elif "result" in data and "offers" in data["result"]:
                        offers = data.get("result", {}).get("offers", [])
                    else:
                        # Try direct array
                        offers = data if isinstance(data, list) else []
                    
                    print(f"📦 Found {len(offers)} offers")
                    # Log raw Yandex API response for debugging
                    if offers:
                        print("=" * 80)
                        print(f"RAW YANDEX API RESPONSE (Campaign API - offers.json) - ALL {len(offers)} PRODUCTS:")
                        print("=" * 80)
                        import json
                        print(json.dumps(offers, indent=2, ensure_ascii=False))
                        print("=" * 80)
                    return offers
                except httpx.HTTPError as e:
                    last_error = e
                    print(f"⚠️  {url} failed, trying next endpoint...")
                    continue
            
            # If all attempts failed, raise the last error
            print(f"❌ Error getting products from Campaign API: {str(last_error)}")
            if hasattr(last_error, 'response') and last_error.response:
                print(f"Response status: {last_error.response.status_code}")
                print(f"Response body: {last_error.response.text}")
            raise Exception(f"Failed to get products from Yandex Market: {str(last_error)}")
        else:
            # Business API uses POST to /offer-mappings (not GET)
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings"
            try:
                response = self._make_request("POST", url, json={}, headers=self._get_headers(), timeout=30.0)
                response.raise_for_status()
                data = response.json()
                # Business API: result.offerMappingEntries
                offer_mappings = data.get("result", {}).get("offerMappingEntries", [])
                # Log raw Yandex API response for debugging
                if offer_mappings:
                    print("=" * 80)
                    print(f"RAW YANDEX API RESPONSE (Business API - offer-mappings) - ALL {len(offer_mappings)} PRODUCTS:")
                    print("=" * 80)
                    import json
                    print(json.dumps(offer_mappings, indent=2, ensure_ascii=False))
                    print("=" * 80)
                return offer_mappings
            except httpx.HTTPError as e:
                print(f"❌ Error getting products from Business API: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    print(f"Response status: {e.response.status_code}")
                    print(f"Response body: {e.response.text}")
                raise Exception(f"Failed to get products from Yandex Market: {str(e)}")
    
    def get_product_card(self, offer_id: str) -> Optional[Dict]:
        """
        Get full product card details from Yandex Market (name, description, images, videos, characteristics, etc.)
        This endpoint provides complete product information including media attachments.
        
        Uses Business API endpoint /v2/businesses/*/offer-cards which works with both ACMA and OAuth tokens
        as long as business_id is available. The Campaign API endpoint is deprecated.
        """
        # Use Business API endpoint if business_id is available (works with both ACMA and OAuth tokens)
        # The Campaign API offer-mapping-entries endpoint is deprecated
        if not self.business_id or (isinstance(self.business_id, str) and not self.business_id.strip()):
            print(f"⚠️  Warning: business_id is required to fetch product card. Skipping product card fetch for {offer_id}")
            return None
        
        try:
            # Business API: Use POST /v2/businesses/*/offer-cards (works with both ACMA and OAuth tokens)
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-cards"
            payload = {
                "offerIds": [offer_id]
            }
            response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            # Business API returns result.offerCards array
            cards = data.get("result", {}).get("offerCards", [])
            if cards:
                card_data = cards[0]
                # Log the raw response
                print("=" * 80)
                print(f"RAW YANDEX PRODUCT CARD API RESPONSE (Business API) FOR {offer_id}:")
                print("=" * 80)
                import json
                print(json.dumps(card_data, indent=2, ensure_ascii=False))
                print("=" * 80)
                return card_data
            return None
        except httpx.HTTPError as e:
            print(f"⚠️  Warning: Could not fetch product card for {offer_id}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            # Don't raise - return None so we can still use basic offer data
            return None
        except Exception as e:
            print(f"⚠️  Warning: Error fetching product card for {offer_id}: {str(e)}")
            return None
    
    def get_orders(self, status: Optional[str] = None, include_test: bool = True) -> List[Dict]:
        """Get orders from Yandex Market
        
        Yandex Market order response format:
        {
            "orders": [
                {
                    "id": 12345,
                    "status": "PROCESSING",
                    "items": [
                        {
                            "id": 987654,       # Item ID (needed for deliverDigitalGoods)
                            "offerId": "MRKT-SJD3W00P",  # Matches Product.yandex_market_id
                            "offerName": "Product Name",
                            "count": 1,
                            "price": 100.0,
                            "digitalItem": true
                        }
                    ],
                    "buyer": {"id": "...", "type": "PERSON"},
                    "total": 100.0,
                    "itemsTotal": 100.0
                }
            ]
        }
        """
        all_orders = []
        
        # Campaign API is the primary endpoint for orders (works with both ACMA and OAuth tokens if campaign_id is set)
        if self.campaign_id:
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/orders"
            params = {
                "page": 1,
                "pageSize": 50,
            }
            if status:
                params["status"] = status
            
            try:
                print(f"🔍 Fetching orders from Campaign API: {url}")
                response = self._make_request("GET", url, params=params, headers=self._get_headers(), timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                # LOG RAW YANDEX API RESPONSE - NO MODIFICATIONS
                print("=" * 80)
                print(f"📋 RAW YANDEX CAMPAIGN API ORDERS RESPONSE (UNMODIFIED):")
                print("=" * 80)
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("=" * 80)
                
                orders = data.get("orders", [])
                print(f"📋 Found {len(orders)} orders from Campaign API")
                if orders:
                    print(f"📦 Summary: {len(orders)} orders found")
                    for order in orders:
                        print(f"  Order #{order.get('id')}: status={order.get('status')}, "
                              f"items={len(order.get('items', []))}, "
                              f"total={order.get('total', order.get('itemsTotal', 0))}, "
                              f"fake={order.get('fake', False)}")
                        for item in order.get('items', []):
                            print(f"    Item #{item.get('id')}: offerId={item.get('offerId')}, "
                                  f"name={item.get('offerName')}, count={item.get('count')}, "
                                  f"price={item.get('price')}, digital={item.get('digitalItem', False)}")
                
                all_orders.extend(orders)
            except httpx.HTTPError as e:
                print(f"⚠️  Campaign API orders failed: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    print(f"  Response status: {e.response.status_code}")
                    print(f"  Response body: {e.response.text}")
            
            # Also try to fetch test/fake orders if requested
            if include_test:
                try:
                    test_params = {**params, "fake": "true"}
                    print(f"🔍 Fetching test orders from Campaign API...")
                    response = self._make_request("GET", url, params=test_params, headers=self._get_headers(), timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    test_orders = data.get("orders", [])
                    if test_orders:
                        print(f"🧪 Found {len(test_orders)} test orders")
                        # Avoid duplicates
                        existing_ids = {o.get("id") for o in all_orders}
                        for test_order in test_orders:
                            if test_order.get("id") not in existing_ids:
                                all_orders.append(test_order)
                except Exception as e:
                    print(f"⚠️  Could not fetch test orders: {str(e)}")
        
        elif self.business_id:
            # Fallback: Business API for orders (if no campaign_id)
            url = f"{self.base_url}/v2/businesses/{self.business_id}/orders"
            params = {}
            if status:
                params["status"] = status
            
            try:
                print(f"🔍 Fetching orders from Business API: {url}")
                response = self._make_request("GET", url, params=params, headers=self._get_headers(), timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                # LOG RAW YANDEX API RESPONSE - NO MODIFICATIONS
                print("=" * 80)
                print(f"📋 RAW YANDEX BUSINESS API ORDERS RESPONSE (UNMODIFIED):")
                print("=" * 80)
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("=" * 80)
                
                orders = data.get("result", {}).get("orders", data.get("orders", []))
                print(f"📋 Found {len(orders)} orders from Business API")
                all_orders.extend(orders)
            except httpx.HTTPError as e:
                print(f"❌ Business API orders failed: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    print(f"  Response status: {e.response.status_code}")
                    print(f"  Response body: {e.response.text}")
        else:
            print("❌ No campaign_id or business_id configured - cannot fetch orders")
        
        print(f"📦 Total orders fetched: {len(all_orders)}")
        return all_orders
    
    def get_order(self, order_id: str) -> Dict:
        """Get a single order by ID from Yandex Market
        
        Returns the complete order data including all items.
        This is critical for delivering digital goods - we need ALL items from Yandex.
        """
        if not self.campaign_id:
            raise ValueError("campaign_id is required to get order details")
        
        url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/orders/{order_id}"
        
        try:
            print(f"🔍 Fetching order details from Yandex: {url}")
            response = self._make_request("GET", url, headers=self._get_headers(), timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            # LOG RAW YANDEX API RESPONSE - NO MODIFICATIONS
            print("=" * 80)
            print(f"📋 RAW YANDEX API RESPONSE FOR ORDER {order_id} (UNMODIFIED):")
            print("=" * 80)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("=" * 80)
            
            # Handle different response structures
            if "order" in data:
                order_data = data["order"]
            elif "orders" in data and len(data["orders"]) > 0:
                order_data = data["orders"][0]
            else:
                order_data = data
            
            print(f"✅ Retrieved order {order_id} with {len(order_data.get('items', []))} items")
            return order_data
        except httpx.HTTPError as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response:
                error_detail = f" - Status: {e.response.status_code}, Body: {e.response.text}"
            raise Exception(f"Failed to get order {order_id} from Yandex Market{error_detail}")
    
    def accept_order(self, order_id: str) -> Dict:
        """Accept an order on Yandex Market (for digital products)"""
        if self.is_acma_token:
            # Campaign API uses /orders/{order_id}/status.json endpoint
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/orders/{order_id}/status.json"
            payload = {"status": "PROCESSING"}  # Accept order
        else:
            url = f"{self.base_url}/v1/businesses/{self.business_id}/orders/{order_id}/accept"
            payload = None
        
        try:
            with httpx.Client() as client:
                if payload:
                    response = client.post(
                        url,
                        json=payload,
                        headers=self._get_headers(),
                        timeout=30.0
                    )
                else:
                    response = client.post(
                        url,
                        headers=self._get_headers(),
                        timeout=30.0
                    )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to accept order on Yandex Market: {str(e)}")
    
    def deliver_digital_goods(self, order_id: str, items: List[Dict]) -> Dict:
        """Deliver digital goods for an order (DBS model)
        
        Uses POST /campaigns/{campaignId}/orders/{orderId}/deliverDigitalGoods
        
        Args:
            order_id: Yandex Market order ID
            items: List of items to deliver, each with:
                - id: Order item ID (from order.items[].id)
                - codes: Array of activation codes/keys (REQUIRED - must be array, not single string)
                - slip: Activation instructions (max 10000 chars, can use HTML)
                - activate_till: Activation code expiry date in YYYY-MM-DD format (REQUIRED - snake_case with underscore!)
        
        Example items:
            [{"id": 987654, "codes": ["XXXX-YYYY"], "slip": "Instructions text", "activate_till": "2026-03-08"}]
        """
        if not self.campaign_id:
            raise ValueError("campaign_id is required for deliverDigitalGoods. Set YANDEX_MARKET_CAMPAIGN_ID.")
        
        url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/orders/{order_id}/deliverDigitalGoods"
        
        payload = {
            "items": items
        }
        
        # Debug: Print the actual payload being sent
        import json
        print(f"📤 Delivering digital goods for order {order_id}")
        print(f"   URL: {url}")
        print(f"   Items: {len(items)}")
        print(f"   Payload JSON: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # Verify activate_till is present in all items (snake_case, not camelCase!)
        for idx, item in enumerate(items):
            if "activate_till" not in item or item["activate_till"] is None:
                raise ValueError(f"Item at index {idx} is missing activate_till field: {item}")
            if "codes" not in item or not item["codes"]:
                raise ValueError(f"Item at index {idx} is missing codes array: {item}")
            print(f"   Item {idx}: id={item.get('id')}, codes={item.get('codes')}, activate_till={item.get('activate_till')}")
        
        try:
            # Manually serialize JSON to ensure activateTill is included
            import json as json_lib
            json_bytes = json_lib.dumps(payload, ensure_ascii=False).encode('utf-8')
            
            # Double-check activate_till and codes are in the serialized JSON
            json_str_check = json_bytes.decode('utf-8')
            if '"activate_till"' not in json_str_check:
                raise ValueError(f"activate_till missing from serialized JSON! JSON: {json_str_check}")
            if '"codes"' not in json_str_check:
                raise ValueError(f"codes missing from serialized JSON! JSON: {json_str_check}")
            
            # Use data parameter with manually serialized JSON and explicit Content-Type
            headers = {**self._get_headers(), "Content-Type": "application/json; charset=utf-8"}
            response = self._make_request(
                "POST", url, 
                data=json_bytes,
                headers=headers, 
                timeout=30.0
            )
            response.raise_for_status()
            print(f"✅ Digital goods delivered successfully for order {order_id}")
            # deliverDigitalGoods returns 200 OK with empty body on success
            try:
                return response.json()
            except:
                return {"success": True, "message": "Digital goods delivered"}
        except httpx.HTTPError as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response:
                error_detail = f" - Status: {e.response.status_code}, Body: {e.response.text}"
            raise Exception(f"Failed to deliver digital goods for order {order_id}{error_detail}")
    
    def complete_order(self, order_id: str, activation_code: str, activation_instructions: str, item_id: int = None, activate_till: str = None) -> Dict:
        """Complete an order by delivering digital goods
        
        This is a convenience wrapper around deliver_digital_goods.
        For DBS digital products, uses POST /campaigns/{campaignId}/orders/{orderId}/deliverDigitalGoods
        
        Args:
            order_id: Yandex Market order ID
            activation_code: The activation code/key
            activation_instructions: Full formatted message to send to customer
            item_id: The order item ID (from order.items[].id). Required for digital goods delivery.
            activate_till: Activation code expiry date in YYYY-MM-DD format (date only, no time).
                          Defaults to 30 days from now if not provided.
        """
        if item_id is None:
            raise ValueError("item_id is required for digital goods delivery. "
                           "It should come from the order's items[].id field stored in yandex_order_data.")
        
        # Ensure item_id is an integer (Yandex API expects integer)
        try:
            item_id = int(item_id)
        except (ValueError, TypeError):
            raise ValueError(f"item_id must be a valid integer, got: {type(item_id).__name__} = {item_id}")
        
        # Calculate activate_till date in YYYY-MM-DD format if not provided
        # Yandex Market API requires just the date (YYYY-MM-DD), no time, no timezone
        if not activate_till:
            from datetime import datetime, timedelta
            expiry_date = datetime.utcnow() + timedelta(days=30)
            activate_till = expiry_date.strftime("%Y-%m-%d")
        
        # Ensure activate_till is a non-empty string
        if not activate_till or not isinstance(activate_till, str) or len(activate_till.strip()) == 0:
            raise ValueError(f"activate_till must be a non-empty string in YYYY-MM-DD format, got: {activate_till}")
        
        # Build items array - ensure all fields are properly typed and not None
        # IMPORTANT: Include activateTill in the initial dict construction to ensure it's not dropped
        activate_till_str = str(activate_till).strip() if activate_till else None
        if not activate_till_str:
            raise ValueError(f"activateTill cannot be None or empty. Got: {repr(activate_till)}")
        
        # Yandex Market API requires just YYYY-MM-DD format (date only, no time, no timezone)
        # Extract just the date part if it's a datetime string
        if 'T' in activate_till_str:
            activate_till_str = activate_till_str.split('T')[0]
        if len(activate_till_str) > 10:
            activate_till_str = activate_till_str[:10]
        # Ensure it's in YYYY-MM-DD format
        if len(activate_till_str) != 10 or activate_till_str.count('-') != 2:
            raise ValueError(f"activate_till must be in YYYY-MM-DD format, got: {activate_till_str}")
        
        # Build the complete item dict with all fields at once
        # CRITICAL: Yandex API uses snake_case, not camelCase!
        # Field name must be exactly "activate_till" (with underscore), NOT "activateTill"
        # Also, "codes" must be an array, NOT "code" as a single string
        # Date format: YYYY-MM-DD (just date, not datetime)
        
        # Extract just the date part (YYYY-MM-DD) if it's a datetime string
        activate_till_date = str(activate_till_str).strip()
        if 'T' in activate_till_date:
            activate_till_date = activate_till_date.split('T')[0]
        if len(activate_till_date) > 10:
            activate_till_date = activate_till_date[:10]
        
        item_dict = {
            "id": int(item_id),  # Explicitly convert to int
            "codes": [str(activation_code)] if activation_code else [],  # CRITICAL: Must be array, not single string
            "slip": str(activation_instructions[:10000]) if activation_instructions else "",  # Yandex limits slip to 10000 chars (not 2000!)
            "activate_till": activate_till_date  # CRITICAL: snake_case with underscore, YYYY-MM-DD format
        }
        
        items = [item_dict]
        
        # Debug: Print item structure
        print(f"🔍 Item structure before sending:")
        import json
        print(json.dumps(items, indent=2, ensure_ascii=False))
        print(f"   activate_till in dict: {'activate_till' in item_dict}")
        print(f"   activate_till value: {repr(item_dict.get('activate_till'))}")
        print(f"   codes in dict: {'codes' in item_dict}")
        print(f"   codes value: {repr(item_dict.get('codes'))}")
        
        # Verify the field is actually in the JSON string
        json_str = json.dumps(items, ensure_ascii=False)
        if '"activate_till"' not in json_str:
            raise ValueError(f"activate_till field missing from JSON serialization! JSON: {json_str}")
        if '"codes"' not in json_str:
            raise ValueError(f"codes field missing from JSON serialization! JSON: {json_str}")
        
        return self.deliver_digital_goods(order_id, items)
    
    # Reviews and Comments Management
    def get_product_reviews(self, product_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get product reviews from Yandex Market"""
        # Reviews use Business API endpoint with business_id (works with both ACMA and OAuth tokens)
        if not self.business_id:
            print("⚠️  business_id is required for reviews. Reviews are not available without business_id.")
            return []
        
        url = f"{self.base_url}/v2/businesses/{self.business_id}/goods-feedback"

        try:
            if self.is_acma_token:
                # ACMA tokens use POST for Business API endpoints
                payload: Dict = {"limit": limit}
                if product_id:
                    payload["productId"] = product_id
                response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
            else:
                # OAuth tokens use GET
                params = {"limit": limit}
                if product_id:
                    params["productId"] = product_id
                response = self._make_request("GET", url, params=params, headers=self._get_headers(), timeout=30.0)
            
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            result = data.get("result", {})
            if "feedbacks" in result:
                # ACMA returns "feedbacks", normalize to "reviews" format
                feedbacks = result.get("feedbacks", [])
                reviews = []
                for feedback in feedbacks:
                    review = {
                        "id": feedback.get("id"),
                        "rating": feedback.get("grade", 0),  # ACMA uses "grade" instead of "rating"
                        "text": feedback.get("text", ""),
                        "author": {
                            "name": feedback.get("author", {}).get("name", "Anonymous") if isinstance(feedback.get("author"), dict) else "Anonymous",
                            "id": feedback.get("author", {}).get("id") if isinstance(feedback.get("author"), dict) else None,
                        },
                        "created_at": feedback.get("createdAt") or feedback.get("created_at"),
                        "product": feedback.get("product", {}),
                    }
                    reviews.append(review)
                return reviews
            else:
                # OAuth returns "reviews"
                return result.get("reviews", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get product reviews: {str(e)}")
    
    def reply_to_review(self, review_id: str, reply_text: str) -> Dict:
        """Reply to a product review"""
        if not self.business_id:
            raise ValueError("business_id is required to reply to reviews")
        
        url = f"{self.base_url}/v2/businesses/{self.business_id}/goods-feedback/comments/update"
        payload = {"text": reply_text, "gradeId": review_id}
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to reply to review: {str(e)}")
    
    def get_shop_reviews(self, limit: int = 50) -> List[Dict]:
        """Get shop reviews from Yandex Market"""
        # Reviews use Business API endpoint with business_id (works with both ACMA and OAuth tokens)
        if not self.business_id or (isinstance(self.business_id, str) and not self.business_id.strip()):
            print("⚠️  business_id is required for reviews. Reviews are not available without business_id.")
            print(f"   Current business_id value: {repr(self.business_id)}")
            return []
        
        url = f"{self.base_url}/v2/businesses/{self.business_id}/goods-feedback"

        try:
            if self.is_acma_token:
                # ACMA tokens use POST for Business API endpoints
                payload: Dict = {"limit": limit}
                response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
            else:
                # OAuth tokens use GET
                params = {"limit": limit}
                response = self._make_request("GET", url, params=params, headers=self._get_headers(), timeout=30.0)
            
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            result = data.get("result", {})
            if "feedbacks" in result:
                # ACMA returns "feedbacks", normalize to "reviews" format
                feedbacks = result.get("feedbacks", [])
                reviews = []
                for feedback in feedbacks:
                    review = {
                        "id": feedback.get("id"),
                        "rating": feedback.get("grade", 0),  # ACMA uses "grade" instead of "rating"
                        "text": feedback.get("text", ""),
                        "author": {
                            "name": feedback.get("author", {}).get("name", "Anonymous") if isinstance(feedback.get("author"), dict) else "Anonymous",
                            "id": feedback.get("author", {}).get("id") if isinstance(feedback.get("author"), dict) else None,
                        },
                        "created_at": feedback.get("createdAt") or feedback.get("created_at"),
                    }
                    reviews.append(review)
                return reviews
            else:
                # OAuth returns "reviews"
                return result.get("reviews", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get shop reviews: {str(e)}")
    
    def reply_to_shop_review(self, review_id: str, reply_text: str) -> Dict:
        """Reply to a shop review"""
        if not self.business_id:
            raise ValueError("business_id is required to reply to reviews")
        
        url = f"{self.base_url}/v2/businesses/{self.business_id}/goods-feedback/comments/update"
        payload = {"text": reply_text, "gradeId": review_id}
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to reply to shop review: {str(e)}")
    
    # Order Chat Management
    def get_order_chat_messages(self, order_id: str) -> List[Dict]:
        """Get chat messages for an order
        
        According to Yandex API documentation:
        - First get the chat for the order using POST /v2/businesses/{businessId}/chats with orderIds filter
        - Then get the chat history using POST /v2/businesses/{businessId}/chats/history with chatId query parameter
        """
        if not self.business_id:
            raise ValueError("business_id is required for chat operations")
        
        # Step 1: Get the chat for this order
        # According to docs: POST /v2/businesses/{businessId}/chats with body containing orderIds
        url = f"{self.base_url}/v2/businesses/{self.business_id}/chats"
        
        try:
            with httpx.Client() as client:
                # Use POST with orderIds filter in body (as per documentation)
                # Note: API only allows ONE filter type - either orderIds, contextTypes, or contexts
                payload = {
                    "orderIds": [int(order_id)]
                }
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 404:
                    # No chat exists yet, return empty list
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                # Handle response structure - result.chats array
                chats = data.get("result", {}).get("chats", [])
                if not chats:
                    # No chat found for this order
                    return []
                
                # Get the first chat (there should typically be one chat per order)
                chat = chats[0]
                chat_id = chat.get("chatId")  # Note: field is "chatId", not "id"
                
                if not chat_id:
                    return []
                
                # Step 2: Get chat history using chat ID
                # According to docs: POST /v2/businesses/{businessId}/chats/history with chatId query parameter
                history_url = f"{self.base_url}/v2/businesses/{self.business_id}/chats/history"
                
                history_response = client.post(
                    history_url,
                    params={"chatId": chat_id},
                    json={},  # Optional body with messageIdFrom if needed
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    messages = history_data.get("result", {}).get("messages", [])
                    return messages
                else:
                    # If history endpoint fails, return empty list
                    print(f"⚠️  Failed to get chat history: {history_response.status_code} - {history_response.text}")
                    return []
                
        except httpx.HTTPError as e:
            error_msg = f"Failed to get order chat messages for order {order_id}"
            if hasattr(e, 'response') and e.response:
                error_msg += f": {e.response.status_code} - {e.response.text}"
            print(f"⚠️  {error_msg}")
            # Return empty list instead of raising to prevent 500 errors
            return []
        except Exception as e:
            print(f"⚠️  Error getting chat messages: {str(e)}")
            return []
    
    def send_order_chat_message(self, order_id: str, message_text: str) -> Dict:
        """Send a message in order chat
        
        According to Yandex API documentation:
        - First get the chat for the order using POST /v2/businesses/{businessId}/chats
        - Then send message using POST /v2/businesses/{businessId}/chats/message with chatId query parameter
        """
        if not self.business_id:
            raise ValueError("business_id is required for chat operations")
        
        # Step 1: Get chat for the order
        chats_url = f"{self.base_url}/v2/businesses/{self.business_id}/chats"
        
        try:
            with httpx.Client() as client:
                # Get existing chat using POST with orderIds filter
                # Note: API only allows ONE filter type - either orderIds, contextTypes, or contexts
                payload = {
                    "orderIds": [int(order_id)]
                }
                response = client.post(
                    chats_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                chat_id = None
                if response.status_code == 200:
                    data = response.json()
                    chats = data.get("result", {}).get("chats", [])
                    if chats:
                        chat_id = chats[0].get("chatId")  # Note: field is "chatId", not "id"
                
                # If no chat exists, we need to create one first
                # According to docs, we might need to use createChat endpoint, but for now
                # we'll try to send anyway - Yandex might auto-create the chat
                if not chat_id:
                    # Try to get chat by orderId using GET /v2/businesses/{businessId}/chat endpoint
                    get_chat_url = f"{self.base_url}/v2/businesses/{self.business_id}/chat"
                    get_chat_response = client.get(
                        get_chat_url,
                        params={"orderId": order_id},
                        headers=self._get_headers(),
                        timeout=30.0
                    )
                    if get_chat_response.status_code == 200:
                        chat_data = get_chat_response.json()
                        chat_id = chat_data.get("result", {}).get("chatId")
                
                if not chat_id:
                    raise ValueError(f"Could not find chat for order {order_id}. Chat may need to be created first.")
                
                # Step 2: Send message to the chat
                # According to docs: POST /v2/businesses/{businessId}/chats/message with chatId query parameter
                send_url = f"{self.base_url}/v2/businesses/{self.business_id}/chats/message"
                
                send_response = client.post(
                    send_url,
                    params={"chatId": chat_id},
                    json={"message": message_text},  # Body contains "message" field, not "text"
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                send_response.raise_for_status()
                return send_response.json()
                
        except httpx.HTTPError as e:
            error_msg = f"Failed to send order chat message for order {order_id}"
            if hasattr(e, 'response') and e.response:
                error_msg += f": {e.response.status_code} - {e.response.text}"
            raise Exception(error_msg)
    
    def download_media_file(self, url: str, save_path: Path) -> str:
        """Download a media file from URL and save it locally"""
        try:
            with httpx.Client() as client:
                response = client.get(url, timeout=60.0, follow_redirects=True)
                response.raise_for_status()
                
                # Ensure directory exists
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save file
                with open(save_path, "wb") as f:
                    f.write(response.content)
                
                # Return relative path
                return str(save_path.relative_to(Path("media")))
        except httpx.HTTPError as e:
            raise Exception(f"Failed to download media file: {str(e)}")
    
    def download_product_media(self, product_data: Dict, media_dir: Path) -> tuple[List[str], List[str]]:
        """Download all media files for a product from Yandex Market"""
        images = []
        videos = []
        
        # Get images from product data
        product_images = product_data.get("pictures", []) or product_data.get("images", [])
        for idx, img_url in enumerate(product_images):
            if not img_url:
                continue
            try:
                # Determine file extension from URL or content type
                parsed_url = urlparse(img_url)
                ext = Path(parsed_url.path).suffix or ".jpg"
                filename = f"product_{product_data.get('id', 'unknown')}_img_{idx}{ext}"
                save_path = media_dir / "images" / filename
                
                relative_path = self.download_media_file(img_url, save_path)
                images.append(relative_path)
            except Exception as e:
                print(f"Failed to download image {img_url}: {str(e)}")
                continue
        
        # Get videos from product data
        product_videos = product_data.get("videos", [])
        for idx, vid_url in enumerate(product_videos):
            if not vid_url:
                continue
            try:
                parsed_url = urlparse(vid_url)
                ext = Path(parsed_url.path).suffix or ".mp4"
                filename = f"product_{product_data.get('id', 'unknown')}_vid_{idx}{ext}"
                save_path = media_dir / "videos" / filename
                
                relative_path = self.download_media_file(vid_url, save_path)
                videos.append(relative_path)
            except Exception as e:
                print(f"Failed to download video {vid_url}: {str(e)}")
                continue
        
        return images, videos
    
    # Inventory and Stock Management
    def update_product_stock(self, shop_sku: str, count: int, warehouse_id: Optional[int] = None) -> Dict:
        """
        Update product stock/quantity on Yandex Market
        For individual entrepreneurs (ИП), stock management is available for FBS and DBS models
        """
        url = f"{self.base_url}/v2/businesses/{self.business_id}/warehouses"
        
        items = [{
            "sku": shop_sku,
            "count": count
        }]
        
        if warehouse_id:
            items[0]["warehouseId"] = warehouse_id
        
        payload = {"skus": items}
        
        try:
            with httpx.Client() as client:
                response = client.put(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update product stock: {str(e)}")
    
    def update_bulk_stocks(self, stocks: List[Dict[str, int]]) -> Dict:
        """
        Update stock for multiple products at once
        stocks: List of dicts with 'sku' and 'count' keys
        """
        url = f"{self.base_url}/v2/businesses/{self.business_id}/warehouses"
        
        items = [{"sku": stock["sku"], "count": stock["count"]} for stock in stocks]
        payload = {"skus": items}
        
        try:
            with httpx.Client() as client:
                response = client.put(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update bulk stocks: {str(e)}")
    
    def get_product_stock(self, shop_sku: str) -> Dict:
        """Get current stock/quantity for a product"""
        url = f"{self.base_url}/v2/businesses/{self.business_id}/warehouses"
        params = {"sku": shop_sku}
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result", {})
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get product stock: {str(e)}")
    
    # Price Management
    def update_product_price(self, shop_sku: str, price: float, old_price: Optional[float] = None) -> Dict:
        """
        Update product price on Yandex Market
        Can update price separately from other product data
        """
        url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-prices/updates"
        
        items = [{
            "offerId": shop_sku,
            "price": {
                "value": price,
                "currencyId": "RUR"
            }
        }]
        
        if old_price:
            items[0]["price"]["oldValue"] = old_price
        
        payload = {"offers": items}
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update product price: {str(e)}")
    
    def update_bulk_prices(self, prices: List[Dict[str, float]]) -> Dict:
        """
        Update prices for multiple products at once
        prices: List of dicts with 'sku', 'price', and optionally 'old_price' keys
        """
        url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-prices/updates"
        
        items = []
        for price_data in prices:
            item = {
                "offerId": price_data["sku"],
                "price": {
                    "value": price_data["price"],
                    "currencyId": "RUR"
                }
            }
            if "old_price" in price_data:
                item["price"]["oldValue"] = price_data["old_price"]
            items.append(item)
        
        payload = {"offers": items}
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update bulk prices: {str(e)}")
    
    # Product Visibility Management
    def update_product_availability(self, shop_sku: str, available: bool) -> Dict:
        """
        Update product availability/visibility on storefront
        available: True for ACTIVE, False for INACTIVE
        """
        # Business API uses offer-mappings/update for all product updates
        if self.is_acma_token:
            # Campaign API: Use POST /v2/campaigns/*/offers/update or POST /v2/campaigns/*/offer-mapping-entries/updates
            # Based on endpoint list: POST /v2/campaigns/*/offers/update exists
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers/update"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings/update"
        
        payload = {
            "offerMappings": [{
                "offer": {
                    "shopSku": shop_sku,
                    "availability": "ACTIVE" if available else "INACTIVE"
                }
            }]
        }
        
        try:
            response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update product availability: {str(e)}")
    
    def update_bulk_availability(self, availabilities: List[Dict[str, bool]]) -> Dict:
        """
        Update availability for multiple products at once
        availabilities: List of dicts with 'sku' and 'available' keys
        """
        results = []
        errors = []
        
        for avail_data in availabilities:
            try:
                result = self.update_product_availability(avail_data["sku"], avail_data["available"])
                results.append(result)
            except Exception as e:
                errors.append(f"Failed to update {avail_data['sku']}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "updated": len(results),
            "errors": errors
        }
    
    # Document Management (for product specifications, certificates, etc.)
    def upload_product_document(self, shop_sku: str, document_url: str, document_type: str = "SPECIFICATION") -> Dict:
        """
        Upload/attach a document to a product
        document_type: SPECIFICATION, CERTIFICATE, MANUAL, etc.
        Note: Document endpoints may not be available in Business API
        """
        if self.is_acma_token:
            # Campaign API: Use POST /v2/campaigns/*/offers/update or POST /v2/campaigns/*/offer-mapping-entries/updates
            # Based on endpoint list: POST /v2/campaigns/*/offers/update exists
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers/update"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings/update"
        
        payload = {
            "document": {
                "type": document_type,
                "url": document_url
            }
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to upload product document: {str(e)}")
    
    def get_product_documents(self, shop_sku: str) -> List[Dict]:
        """Get all documents attached to a product"""
        # Note: May need to use offer-mappings with specific SKU filter
        if self.is_acma_token:
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offer-mapping-entries"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings"
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result", {}).get("documents", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get product documents: {str(e)}")
    
    def delete_product_document(self, shop_sku: str, document_id: str) -> Dict:
        """Delete a document from a product"""
        # Document deletion may not be available in Business API
        if self.is_acma_token:
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offer-mapping-entries"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings"
        
        try:
            with httpx.Client() as client:
                response = client.delete(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to delete product document: {str(e)}")
    
    def delete_product(self, shop_sku: str) -> Dict:
        """Delete a product from Yandex Market"""
        if self.is_acma_token:
            # Campaign API uses POST /offers/delete with offerIds array
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers/delete"
            payload = {"offerIds": [shop_sku]}
            try:
                response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
                response.raise_for_status()
                # Delete endpoint may return 204 No Content
                if response.status_code == 204:
                    return {"success": True, "message": "Product deleted successfully"}
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to delete product from Yandex: {str(e)}")
        else:
            # Business API uses POST with payload
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings/delete"
            payload = {"offerIds": [shop_sku]}
            try:
                response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
                response.raise_for_status()
                # Delete endpoint may return 204 No Content
                if response.status_code == 204:
                    return {"success": True, "message": "Product deleted successfully"}
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to delete product from Yandex: {str(e)}")
    
    # Bulk Product Operations
    def create_bulk_products(self, products: List[models.Product]) -> Dict:
        """
        Create multiple products at once (bulk operation)
        More efficient than creating products one by one
        """
        if self.is_acma_token:
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offer-mapping-entries"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings"
        
        offers = []
        for product in products:
            offer = self._build_offer_payload(product)
            offers.append(offer)
        
        payload = {"offers": offers}
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60.0  # Longer timeout for bulk operations
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to create bulk products: {str(e)}")
    
    def update_bulk_products(self, products: List[models.Product]) -> Dict:
        """
        Update multiple products at once (bulk operation)
        """
        results = []
        errors = []
        
        for product in products:
            if not product.yandex_market_id:
                errors.append(f"Product {product.id} not synced with Yandex Market")
                continue
            
            try:
                result = self.update_product(product)
                results.append(result)
            except Exception as e:
                errors.append(f"Failed to update product {product.id}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "updated": len(results),
            "errors": errors
        }
    
    # Helper method to build offer payload (extracted for reuse)
    def _build_offer_payload(self, product: models.Product) -> Dict:
        """Build offer payload from product model"""
        # Get images and videos from yandex_full_data if available
        images = []
        videos = []
        if product.yandex_full_data:
            images = product.yandex_full_data.get("pictures") or product.yandex_full_data.get("images") or []
            videos = product.yandex_full_data.get("videos") or []
            if not isinstance(images, list):
                images = []
            if not isinstance(videos, list):
                videos = []
        
        offer = {
            "shopSku": product.yandex_market_sku or f"SKU-{product.id}",
            "name": product.name,
            "description": product.description or "",
            "price": product.selling_price,
            "vat": "VAT_20",
            "availability": "ACTIVE" if product.is_active else "INACTIVE",
        }
        
        # For digital products, use DBS model
        if product.product_type == models.ProductType.DIGITAL:
            offer["type"] = "DIGITAL"
            offer["model"] = product.yandex_model or "DBS"
        else:
            offer["type"] = "PHYSICAL"
            if product.yandex_model:
                offer["model"] = product.yandex_model
        
        # Category information
        if product.yandex_category_id:
            offer["categoryId"] = product.yandex_category_id
        elif product.yandex_category_path:
            offer["category"] = product.yandex_category_path
        
        # Product parameters
        params = {}
        if product.yandex_brand:
            params["vendor"] = product.yandex_brand
        if product.yandex_platform:
            params["platform"] = product.yandex_platform
        if product.yandex_localization:
            params["localization"] = product.yandex_localization
        if product.yandex_publication_type:
            params["publicationType"] = product.yandex_publication_type
        if product.yandex_activation_territory:
            params["activationTerritory"] = product.yandex_activation_territory
        if product.yandex_edition:
            params["edition"] = product.yandex_edition
        if product.yandex_series:
            params["series"] = product.yandex_series
        if product.yandex_age_restriction:
            params["ageRestriction"] = product.yandex_age_restriction
        if product.yandex_activation_instructions is not None:
            params["hasActivationInstructions"] = product.yandex_activation_instructions
        
        if params:
            offer["params"] = params
        
        # Pricing with discount
        if product.original_price and product.original_price > product.selling_price:
            offer["oldPrice"] = product.original_price
        
        # Media
        if images:
            offer["pictures"] = images
        if videos:
            offer["videos"] = videos
        
        return offer
    
    # Get product by SKU with full details
    def get_product_by_sku(self, shop_sku: str) -> Optional[Dict]:
        """Get a specific product by SKU with all details"""
        if self.is_acma_token:
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offer-mapping-entries"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings"
        params = {"shopSku": shop_sku}
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                entries = data.get("result", {}).get("offerMappingEntries", [])
                return entries[0] if entries else None
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get product by SKU: {str(e)}")
    
    # Update only product specifications/parameters (without changing other fields)
    def update_product_specifications(self, shop_sku: str, specifications: Dict) -> Dict:
        """
        Update only product specifications/parameters
        specifications: Dict with parameter keys and values
        """
        # Business API uses offer-mappings/update
        if self.is_acma_token:
            # Campaign API: Use POST /v2/campaigns/*/offers/update or POST /v2/campaigns/*/offer-mapping-entries/updates
            # Based on endpoint list: POST /v2/campaigns/*/offers/update exists
            url = f"{self.base_url}/v2/campaigns/{self.campaign_id}/offers/update"
        else:
            url = f"{self.base_url}/v2/businesses/{self.business_id}/offer-mappings/update"
        
        payload = {
            "offerMappings": [{
                "offer": {
                    "shopSku": shop_sku,
                    "params": specifications
                }
            }]
        }
        
        try:
            response = self._make_request("POST", url, json=payload, headers=self._get_headers(), timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to update product specifications: {str(e)}")