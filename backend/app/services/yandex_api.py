import httpx
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse
from app.config import settings
from app import models


class YandexMarketAPI:
    """Service for interacting with Yandex Market Partner API"""
    
    def __init__(self):
        self.base_url = settings.YANDEX_MARKET_API_URL
        self.api_token = settings.YANDEX_MARKET_API_TOKEN
        self.campaign_id = settings.YANDEX_MARKET_CAMPAIGN_ID
        
        if not self.api_token:
            raise ValueError("YANDEX_MARKET_API_TOKEN is required. Create a token in Yandex Market Partner dashboard.")
        if not self.campaign_id:
            raise ValueError("YANDEX_MARKET_CAMPAIGN_ID is required. Find it in your Yandex Market Partner dashboard.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"OAuth {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def create_product(self, product: models.Product) -> Dict:
        """Create a product on Yandex Market with all available fields"""
        # Yandex Market API endpoint for creating products
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries"
        
        # Parse images and videos from JSON strings
        images = []
        videos = []
        if product.yandex_images:
            try:
                images = json.loads(product.yandex_images) if isinstance(product.yandex_images, str) else product.yandex_images
            except:
                images = []
        if product.yandex_videos:
            try:
                videos = json.loads(product.yandex_videos) if isinstance(product.yandex_videos, str) else product.yandex_videos
            except:
                videos = []
        
        # Build offer payload with all fields
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
            # DBS (Digital By Seller) model is required for digital products
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
        
        # Product details
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
        if product.yandex_activation_instructions:
            params["hasActivationInstructions"] = product.yandex_activation_instructions
        
        # Pricing with discount
        if product.original_price and product.original_price > product.selling_price:
            offer["oldPrice"] = product.original_price
            # Calculate discount if not set
            if not product.discount_percentage:
                product.discount_percentage = ((product.original_price - product.selling_price) / product.original_price) * 100
        
        # Images
        if images:
            offer["pictures"] = images
        
        # Videos
        if videos:
            offer["videos"] = videos
        
        # Add params if any
        if params:
            offer["params"] = params
        
        payload = {"offer": offer}
        
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
            raise Exception(f"Failed to create product on Yandex Market: {str(e)}")
    
    def update_product(self, product: models.Product) -> Dict:
        """Update a product on Yandex Market with all available fields"""
        if not product.yandex_market_id:
            raise ValueError("Product not synced with Yandex Market")
        
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries/{product.yandex_market_id}"
        
        # Parse images and videos from JSON strings
        images = []
        videos = []
        if product.yandex_images:
            try:
                image_paths = json.loads(product.yandex_images) if isinstance(product.yandex_images, str) else product.yandex_images
                # Convert local paths to full URLs for Yandex
                for path in image_paths:
                    if path and not path.startswith("http"):
                        # Local file - convert to full URL
                        from app.config import settings
                        base_url = settings.PUBLIC_URL
                        images.append(f"{base_url}/api/media/files/{path}")
                    else:
                        images.append(path)
            except:
                images = []
        if product.yandex_videos:
            try:
                video_paths = json.loads(product.yandex_videos) if isinstance(product.yandex_videos, str) else product.yandex_videos
                # Convert local paths to full URLs for Yandex
                for path in video_paths:
                    if path and not path.startswith("http"):
                        # Local file - convert to full URL
                        from app.config import settings
                        base_url = settings.PUBLIC_URL
                        videos.append(f"{base_url}/api/media/files/{path}")
                    else:
                        videos.append(path)
            except:
                videos = []
        
        # Build offer payload with all fields
        offer = {
            "name": product.name,
            "description": product.description or "",
            "price": product.selling_price,
            "availability": "ACTIVE" if product.is_active else "INACTIVE",
        }
        
        # For digital products, ensure DBS model
        if product.product_type == models.ProductType.DIGITAL:
            offer["model"] = product.yandex_model or "DBS"
        elif product.yandex_model:
            offer["model"] = product.yandex_model
        
        # Category information
        if product.yandex_category_id:
            offer["categoryId"] = product.yandex_category_id
        elif product.yandex_category_path:
            offer["category"] = product.yandex_category_path
        
        # Product details
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
        
        # Pricing with discount
        if product.original_price and product.original_price > product.selling_price:
            offer["oldPrice"] = product.original_price
        
        # Images
        if images:
            offer["pictures"] = images
        
        # Videos
        if videos:
            offer["videos"] = videos
        
        # Add params if any
        if params:
            offer["params"] = params
        
        payload = {"offer": offer}
        
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
            raise Exception(f"Failed to update product on Yandex Market: {str(e)}")
    
    def get_products(self) -> List[Dict]:
        """Get all products from Yandex Market"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries"
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result", {}).get("offerMappingEntries", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get products from Yandex Market: {str(e)}")
    
    def get_orders(self, status: Optional[str] = None) -> List[Dict]:
        """Get orders from Yandex Market"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/orders"
        
        params = {}
        if status:
            params["status"] = status
        
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
                return data.get("result", {}).get("orders", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get orders from Yandex Market: {str(e)}")
    
    def accept_order(self, order_id: str) -> Dict:
        """Accept an order on Yandex Market (for digital products)"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}/accept"
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to accept order on Yandex Market: {str(e)}")
    
    def complete_order(self, order_id: str, activation_code: str) -> Dict:
        """Complete an order by providing activation code"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}/status"
        
        payload = {
            "status": "DELIVERED",
            "substatus": "DELIVERED",
            "digitalGoods": {
                "activationCode": activation_code,
                "activationInstructions": "Please check your email for activation instructions."
            }
        }
        
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
            raise Exception(f"Failed to complete order on Yandex Market: {str(e)}")
    
    # Reviews and Comments Management
    def get_product_reviews(self, product_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get product reviews from Yandex Market"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/reviews"
        params = {"limit": limit}
        if product_id:
            params["productId"] = product_id
        
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
                return data.get("result", {}).get("reviews", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get product reviews: {str(e)}")
    
    def reply_to_review(self, review_id: str, reply_text: str) -> Dict:
        """Reply to a product review"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/reviews/{review_id}/reply"
        payload = {"text": reply_text}
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/shop-reviews"
        params = {"limit": limit}
        
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
                return data.get("result", {}).get("reviews", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get shop reviews: {str(e)}")
    
    def reply_to_shop_review(self, review_id: str, reply_text: str) -> Dict:
        """Reply to a shop review"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/shop-reviews/{review_id}/reply"
        payload = {"text": reply_text}
        
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
        """Get chat messages for an order"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}/chat"
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("result", {}).get("messages", [])
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get order chat messages: {str(e)}")
    
    def send_order_chat_message(self, order_id: str, message_text: str) -> Dict:
        """Send a message in order chat"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/orders/{order_id}/chat/messages"
        payload = {"text": message_text}
        
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
            raise Exception(f"Failed to send order chat message: {str(e)}")
    
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offers/stocks"
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offers/stocks"
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offers/stocks"
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-prices/updates"
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-prices/updates"
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries/{shop_sku}"
        
        payload = {
            "offer": {
                "availability": "ACTIVE" if available else "INACTIVE"
            }
        }
        
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
        """
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries/{shop_sku}/documents"
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries/{shop_sku}/documents"
        
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries/{shop_sku}/documents/{document_id}"
        
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
    
    # Bulk Product Operations
    def create_bulk_products(self, products: List[models.Product]) -> Dict:
        """
        Create multiple products at once (bulk operation)
        More efficient than creating products one by one
        """
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries"
        
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
        # Parse images and videos
        images = []
        videos = []
        if product.yandex_images:
            try:
                image_paths = json.loads(product.yandex_images) if isinstance(product.yandex_images, str) else product.yandex_images
                for path in image_paths:
                    if path and not path.startswith("http"):
                        from app.config import settings
                        base_url = settings.PUBLIC_URL
                        images.append(f"{base_url}/api/media/files/{path}")
                    else:
                        images.append(path)
            except:
                images = []
        
        if product.yandex_videos:
            try:
                video_paths = json.loads(product.yandex_videos) if isinstance(product.yandex_videos, str) else product.yandex_videos
                for path in video_paths:
                    if path and not path.startswith("http"):
                        from app.config import settings
                        base_url = settings.PUBLIC_URL
                        videos.append(f"{base_url}/api/media/files/{path}")
                    else:
                        videos.append(path)
            except:
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries"
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
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-mapping-entries/{shop_sku}"
        
        payload = {
            "offer": {
                "params": specifications
            }
        }
        
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
            raise Exception(f"Failed to update product specifications: {str(e)}")