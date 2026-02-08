from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.database import engine, Base, SessionLocal
from app.routers import products, orders, dashboard, email_templates as activation_templates, sync, webhooks, reviews, chat, media, inventory, settings as settings_router, clients, marketing_emails, documentations
from app.config import settings
from app.initial_data import create_default_email_template
from app.services.yandex_api import YandexMarketAPI
from app.services.review_checker import review_checker
from app import models
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Thread pool for running synchronous API calls
executor = ThreadPoolExecutor(max_workers=2)

def _is_digital_product(yandex_product_data: dict) -> bool:
    """
    Determine if a product is digital based on Yandex API response.
    
    A product is digital if it has parameterId 37693330 with:
    - valueId 39982970, OR
    - value containing "electronic key" (case-insensitive)
    
    Args:
        yandex_product_data: The full Yandex product data (from offer-cards or offer-mappings)
    
    Returns:
        True if product is digital, False otherwise
    """
    if not yandex_product_data:
        return False
    
    # Check parameterValues array
    parameter_values = yandex_product_data.get("parameterValues", [])
    if not isinstance(parameter_values, list):
        # Debug: log if parameterValues is not a list
        offer_id = yandex_product_data.get("offerId") or yandex_product_data.get("id", "unknown")
        print(f"  ⚠️  Product {offer_id}: parameterValues is not a list: {type(parameter_values)}")
        return False
    
    # Debug: log parameterValues count
    offer_id = yandex_product_data.get("offerId") or yandex_product_data.get("id", "unknown")
    print(f"  🔍 Checking product {offer_id}: found {len(parameter_values)} parameter values")
    
    for param in parameter_values:
        if not isinstance(param, dict):
            continue
        
        # Check for parameterId 37693330 (Product Type parameter)
        param_id = param.get("parameterId")
        if param_id == 37693330:
            # Check valueId 39982970 (electronic key)
            value_id = param.get("valueId")
            if value_id == 39982970:
                print(f"  ✅ Product {offer_id}: Found digital product (valueId 39982970)")
                return True
            
            # Check value string for "electronic key"
            value = param.get("value", "")
            if isinstance(value, str) and "electronic key" in value.lower():
                print(f"  ✅ Product {offer_id}: Found digital product (value contains 'electronic key')")
                return True
    
    print(f"  ❌ Product {offer_id}: Not a digital product (no parameterId 37693330 with electronic key)")
    return False

def _sync_products_sync():
    """Sync products FROM Yandex Market TO local database (one-way sync)
    
    Always updates existing products to reflect changes from Yandex (like status changes).
    Preserves local-only fields (cost_price, supplier info, email_template_id, documentation_id).
    """
    try:
        db = SessionLocal()
        try:
            yandex_api = YandexMarketAPI()
            yandex_products = yandex_api.get_products()
            
            products_created = 0
            products_updated = 0
            
            print(f"📦 Found {len(yandex_products)} products from Yandex Market")
            
            for yandex_product in yandex_products:
                try:
                    # Handle different response structures
                    # Campaign API (offers.json) returns direct offer objects
                    # Business API (offer-mappings) uses "offer" and "mapping" fields
                    if "offer" in yandex_product and "mapping" in yandex_product:
                        # Business API structure: {offer: {...}, mapping: {...}}
                        offer_data = yandex_product.get("offer", {})
                        mapping_data = yandex_product.get("mapping", {})
                        yandex_id = offer_data.get("id") or mapping_data.get("marketSku") or yandex_product.get("id")
                        yandex_sku = offer_data.get("shopSku") or mapping_data.get("shopSku") or yandex_product.get("sku")
                        # Merge offer and mapping data for full product info
                        yandex_product = {**offer_data, **mapping_data, "id": yandex_id, "sku": yandex_sku}
                    else:
                        # Campaign API (offers.json) or direct structure
                        # offers.json returns: {offerId, basicPrice: {value, currencyId}, status, available, ...}
                        yandex_id = yandex_product.get("id") or yandex_product.get("offerId")
                        yandex_sku = yandex_product.get("sku") or yandex_product.get("shopSku") or yandex_product.get("vendorCode") or yandex_id
                    
                    existing_product = db.query(models.Product).filter(
                        (models.Product.yandex_market_id == yandex_id) |
                        (models.Product.yandex_market_sku == yandex_sku)
                    ).first()
                    
                    if existing_product:
                        # Always update existing products to reflect changes from Yandex
                        # Preserve local-only fields (these are not synced from Yandex)
                        preserved_cost_price = existing_product.cost_price
                        preserved_supplier_url = existing_product.supplier_url
                        preserved_supplier_name = existing_product.supplier_name
                        preserved_email_template_id = existing_product.email_template_id
                        preserved_documentation_id = existing_product.documentation_id
                        
                        # Fetch product card to get mapping.marketSkuName and parameterValues
                        try:
                            # Use the yandex_api instance already created at function start
                            product_card = yandex_api.get_product_card(yandex_id)
                            if product_card:
                                # Merge product card data with basic offer data
                                import copy
                                merged_data = copy.deepcopy(yandex_product)
                                merged_data.update(product_card)
                                yandex_product = merged_data
                        except Exception as e:
                            print(f"⚠️  Warning: Could not fetch product card for {yandex_id}: {str(e)}")
                            # If product card fetch fails, try to use stored yandex_full_data if it has parameterValues
                            if existing_product.yandex_full_data and isinstance(existing_product.yandex_full_data, dict):
                                stored_params = existing_product.yandex_full_data.get("parameterValues", [])
                                if isinstance(stored_params, list) and len(stored_params) > 0:
                                    # Merge stored parameterValues into yandex_product
                                    if "parameterValues" not in yandex_product or not yandex_product.get("parameterValues"):
                                        yandex_product["parameterValues"] = stored_params
                        
                        # Store complete Yandex JSON data
                        existing_product.yandex_full_data = yandex_product
                        
                        # Determine product type from Yandex data (check merged data with parameterValues)
                        is_digital = _is_digital_product(yandex_product)
                        existing_product.product_type = models.ProductType.DIGITAL if is_digital else models.ProductType.PHYSICAL
                        
                        # Update with Yandex data (Yandex is source of truth)
                        # Extract product name from mapping.marketSkuName (priority) - this comes from product card
                        product_name = (
                            yandex_product.get("mapping", {}).get("marketSkuName") or
                            yandex_product.get("marketSkuName") or
                            yandex_product.get("name") or
                            existing_product.name or
                            yandex_id  # Fallback to offerId
                        )
                        existing_product.name = product_name
                        existing_product.description = yandex_product.get("description", existing_product.description)
                        
                        # Extract price from basicPrice.value or price field
                        if yandex_product.get("basicPrice"):
                            basic_price = yandex_product.get("basicPrice")
                            if isinstance(basic_price, dict):
                                existing_product.selling_price = basic_price.get("value", existing_product.selling_price)
                            else:
                                existing_product.selling_price = basic_price
                        elif yandex_product.get("price"):
                            price = yandex_product.get("price")
                            if isinstance(price, dict):
                                existing_product.selling_price = price.get("value", existing_product.selling_price)
                            else:
                                existing_product.selling_price = price
                        
                        existing_product.yandex_market_id = yandex_id
                        existing_product.yandex_market_sku = yandex_sku
                        
                        # Update active status from Yandex (always sync this from Yandex)
                        status = yandex_product.get("status", "")
                        if status:
                            # PUBLISHED = active, others = inactive
                            existing_product.is_active = (status == "PUBLISHED")
                        elif "available" in yandex_product:
                            existing_product.is_active = bool(yandex_product.get("available"))
                        # If no status or available field, check if product has basicPrice (indicates it's listed)
                        elif yandex_product.get("basicPrice") or yandex_product.get("price"):
                            existing_product.is_active = True  # Has price, assume active
                        
                        # Restore preserved local-only fields (these are never synced from Yandex)
                        existing_product.cost_price = preserved_cost_price
                        existing_product.supplier_url = preserved_supplier_url
                        existing_product.supplier_name = preserved_supplier_name
                        existing_product.email_template_id = preserved_email_template_id
                        existing_product.documentation_id = preserved_documentation_id
                        
                        existing_product.is_synced = True
                        products_updated += 1
                        print(f"  ✅ Updated existing product: {product_name} (offerId: {yandex_id}, status: {'Active' if existing_product.is_active else 'Inactive'})")
                    else:
                        # Fetch product card to get mapping.marketSkuName for new products
                        try:
                            # Use the yandex_api instance already created at function start
                            product_card = yandex_api.get_product_card(yandex_id)
                            if product_card:
                                # Merge product card data with basic offer data
                                import copy
                                merged_data = copy.deepcopy(yandex_product)
                                merged_data.update(product_card)
                                yandex_product = merged_data
                        except Exception as e:
                            print(f"⚠️  Warning: Could not fetch product card for {yandex_id}: {str(e)}")
                        
                        # Create new product from Yandex
                        # Extract product name from mapping.marketSkuName (priority) - this comes from product card
                        product_name = (
                            yandex_product.get("mapping", {}).get("marketSkuName") or
                            yandex_product.get("marketSkuName") or
                            yandex_product.get("name") or
                            yandex_id or  # Use offerId as fallback name
                            "Unknown Product"
                        )
                        
                        # Extract price from basicPrice.value or price field
                        selling_price = 0
                        if yandex_product.get("basicPrice"):
                            basic_price = yandex_product.get("basicPrice")
                            if isinstance(basic_price, dict):
                                selling_price = basic_price.get("value", 0)
                            else:
                                selling_price = basic_price
                        elif yandex_product.get("price"):
                            price = yandex_product.get("price")
                            if isinstance(price, dict):
                                selling_price = price.get("value", 0)
                            else:
                                selling_price = price
                        
                        # Determine active status from status or available field
                        # Default to True (active) if status is not explicitly set
                        is_active = True
                        status = yandex_product.get("status", "")
                        if status:
                            # PUBLISHED = active, others = inactive
                            is_active = (status == "PUBLISHED")
                        elif "available" in yandex_product:
                            is_active = bool(yandex_product.get("available"))
                        # If no status or available field, check if product has basicPrice (indicates it's listed)
                        elif yandex_product.get("basicPrice") or yandex_product.get("price"):
                            is_active = True  # Has price, assume active
                        # If no status or available field, check if product has basicPrice (indicates it's listed)
                        elif yandex_product.get("basicPrice") or yandex_product.get("price"):
                            is_active = True  # Has price, assume active
                        
                        # Determine product type from Yandex data
                        is_digital = _is_digital_product(yandex_product)
                        
                        new_product = models.Product(
                            name=product_name,
                            description=yandex_product.get("description"),
                            yandex_market_id=yandex_id,
                            yandex_market_sku=yandex_sku,
                            selling_price=selling_price,
                            cost_price=0,
                            is_synced=True,
                            product_type=models.ProductType.DIGITAL if is_digital else models.ProductType.PHYSICAL,
                            is_active=is_active,
                            yandex_full_data=yandex_product  # Store complete Yandex JSON
                        )
                        
                        db.add(new_product)
                        products_created += 1
                        print(f"  ✅ Created new product: {product_name} (offerId: {yandex_id}, price: {selling_price})")
                except Exception as e:
                    print(f"  ⚠️  Error processing product {yandex_id if 'yandex_id' in locals() else 'unknown'}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            db.commit()
            print(f"[Auto-Sync] Products synced from Yandex at {datetime.utcnow()} - Created: {products_created}, Updated: {products_updated}")
        except Exception as e:
            print(f"[Auto-Sync] Error in product sync inner block: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"[Auto-Sync] Error syncing products: {str(e)}")
        import traceback
        traceback.print_exc()

def _parse_yandex_order(yandex_order: dict, db) -> list:
    """Parse a Yandex Market order and create local Order records.
    
    Yandex orders contain an 'items' array. Each item has:
    - id: Item ID (needed for deliverDigitalGoods)
    - offerId: Matches Product.yandex_market_id
    - shopSku: Same as offerId for DBS
    - count: Quantity
    - price: Price per unit
    - digitalItem: True for digital products
    
    Returns list of (new_order, product) tuples created.
    """
    created_orders = []
    yandex_order_id = str(yandex_order.get("id"))
    order_status = yandex_order.get("status", "PENDING")
    items = yandex_order.get("items", [])
    
    # Extract buyer info (Yandex uses 'buyer', not 'customer')
    buyer = yandex_order.get("buyer", {})
    buyer_name = None
    if isinstance(buyer, dict):
        first_name = buyer.get("firstName", "")
        last_name = buyer.get("lastName", "")
        buyer_name = f"{first_name} {last_name}".strip() or None
    
    # Get total amount from order level
    total_amount = yandex_order.get("total") or yandex_order.get("itemsTotal") or yandex_order.get("buyerTotal") or 0
    
    if not items:
        print(f"  ⚠️  Order {yandex_order_id} has no items, skipping")
        return created_orders
    
    print(f"  📦 Order {yandex_order_id} has {len(items)} item(s) - creating Order records for each matched product")
    
    # For each item in the order, try to match with a local product
    # Yandex API is source of truth - create ONE Order record per item
    for idx, item in enumerate(items, 1):
        offer_id = item.get("offerId") or item.get("shopSku")
        shop_sku = item.get("shopSku") or item.get("offerId")
        market_sku = str(item.get("marketSku", "")) if item.get("marketSku") else None
        item_count = item.get("count", 1)
        item_price = item.get("price") or item.get("buyerPrice") or 0
        item_total = float(item_price) * item_count
        
        if not offer_id:
            print(f"  ⚠️  Item in order {yandex_order_id} has no offerId, skipping")
            continue
        
        # Match product by offerId (yandex_market_id) or shopSku (yandex_market_sku) or marketSku
        product = db.query(models.Product).filter(
            (models.Product.yandex_market_id == offer_id) |
            (models.Product.yandex_market_id == shop_sku) |
            (models.Product.yandex_market_sku == offer_id) |
            (models.Product.yandex_market_sku == shop_sku)
        ).first()
        
        # Also try matching by marketSku if available
        if not product and market_sku:
            product = db.query(models.Product).filter(
                (models.Product.yandex_market_sku == market_sku) |
                (models.Product.yandex_market_id == market_sku)
            ).first()
        
        # If still no match, try searching in yandex_full_data JSON field
        if not product:
            # Query all products and check their yandex_full_data for matching offerId/shopSku
            all_products = db.query(models.Product).all()
            for p in all_products:
                if p.yandex_full_data:
                    yandex_data = p.yandex_full_data
                    # Check offerId in yandex_full_data
                    if yandex_data.get("offerId") == offer_id or yandex_data.get("offerId") == shop_sku:
                        product = p
                        break
                    # Check shopSku in yandex_full_data
                    if yandex_data.get("shopSku") == offer_id or yandex_data.get("shopSku") == shop_sku:
                        product = p
                        break
                    # Check mapping.marketSku
                    if yandex_data.get("mapping", {}).get("marketSku") and str(yandex_data.get("mapping", {}).get("marketSku")) == market_sku:
                        product = p
                        break
        
        if not product:
            print(f"  ⚠️  No product found for offerId={offer_id} (shopSku={shop_sku}) in order {yandex_order_id} - skipping this item")
            print(f"      This item will not have an Order record until the product is synced to the database")
            continue
        
        # Map Yandex status to local status
        status_mapping = {
            "PROCESSING": models.OrderStatus.PROCESSING,
            "DELIVERY": models.OrderStatus.PROCESSING,
            "DELIVERED": models.OrderStatus.COMPLETED,
            "CANCELLED": models.OrderStatus.CANCELLED,
            "CANCELLED_IN_PROCESSING": models.OrderStatus.CANCELLED,
            "CANCELLED_IN_DELIVERY": models.OrderStatus.CANCELLED,
            "PENDING": models.OrderStatus.PENDING,
            "UNPAID": models.OrderStatus.PENDING,
            "RESERVED": models.OrderStatus.PENDING,
        }
        local_status = status_mapping.get(order_status, models.OrderStatus.PENDING)
        
        new_order = models.Order(
            yandex_order_id=yandex_order_id,
            product_id=product.id,
            customer_name=buyer_name,
            customer_email=None,  # Yandex doesn't expose buyer email for privacy
            customer_phone=None,  # Yandex doesn't expose buyer phone for privacy
            quantity=item_count,
            total_amount=item_total if item_total > 0 else float(total_amount),
            status=local_status,
            yandex_status=order_status,
            yandex_order_data=yandex_order,  # Store full order data (includes items[].id for delivery)
        )
        
        created_orders.append((new_order, product))
        print(f"    ✅ Item {idx}/{len(items)}: Matched product {product.id} ({product.name}) - will create Order record")
    
    if len(created_orders) < len(items):
        print(f"    ⚠️  Warning: Only {len(created_orders)}/{len(items)} items matched products in database")
    
    return created_orders


def _ensure_digital_products_marked_as_sent(order_records, db):
    """Ensure digital products with COMPLETED or FINISHED status are marked as activation_code_sent = True
    
    This function ensures that any digital product order that is COMPLETED or FINISHED
    automatically shows as having activation codes sent, even if the flag wasn't set.
    """
    try:
        from app import models
        
        for order_record in order_records:
            # Only process digital products
            product = db.query(models.Product).filter(models.Product.id == order_record.product_id).first()
            if not product or product.product_type != models.ProductType.DIGITAL:
                continue
            
            # If status is COMPLETED or FINISHED, ensure activation_code_sent is True
            if order_record.status in [models.OrderStatus.COMPLETED, models.OrderStatus.FINISHED]:
                if not order_record.activation_code_sent:
                    order_record.activation_code_sent = True
                    if not order_record.activation_code_sent_at:
                        order_record.activation_code_sent_at = datetime.utcnow()
                    print(f"  ✅ Marked digital product order {order_record.id} as sent (status: {order_record.status})")
    except Exception as e:
        print(f"  ⚠️  Error ensuring digital products marked as sent: {str(e)}")
        import traceback
        traceback.print_exc()


def _auto_send_activations_for_existing_orders(db):
    """Check for existing orders with activation templates and automatically send activations
    
    This function:
    1. Finds all PROCESSING orders that are digital products
    2. Checks if all products in each order have activation templates
    3. Checks if all products have activation keys assigned
    4. Automatically sends activations for orders that meet all conditions
    5. Updates the database to mark activations as sent
    """
    try:
        from app.services.order_service import OrderService
        from app import models
        
        # Check if auto-activation is enabled
        app_settings = db.query(models.AppSettings).first()
        if not app_settings or not app_settings.auto_activation_enabled:
            print("[Auto-Send Activations] Auto-activation is disabled in settings, skipping...")
            return
        
        print("[Auto-Send Activations] Checking for existing orders with activation templates...")
        
        # Get all PROCESSING orders that haven't sent activation codes yet
        pending_orders = db.query(models.Order).filter(
            models.Order.status == models.OrderStatus.PROCESSING,
            models.Order.activation_code_sent == False
        ).all()
        
        if not pending_orders:
            print("[Auto-Send Activations] No pending orders found")
            return
        
        # Group orders by yandex_order_id
        orders_by_yandex_id = {}
        for order in pending_orders:
            yandex_id = order.yandex_order_id
            if yandex_id not in orders_by_yandex_id:
                orders_by_yandex_id[yandex_id] = []
            orders_by_yandex_id[yandex_id].append(order)
        
        print(f"[Auto-Send Activations] Found {len(orders_by_yandex_id)} unique orders to check")
        
        order_service = OrderService(db)
        activations_sent = 0
        
        # Process each unique order
        for yandex_order_id, order_group in orders_by_yandex_id.items():
            try:
                # Check if all products have activation templates
                all_have_templates, missing_templates = order_service._check_all_products_have_templates(yandex_order_id)
                
                if not all_have_templates:
                    print(f"[Auto-Send Activations] Order {yandex_order_id}: Missing templates for: {', '.join(missing_templates)}")
                    continue
                
                # Check if all products have random_key = True (auto-generated keys)
                # Skip orders that require manual activation keys
                all_have_random_key, products_with_manual_key = order_service._check_all_products_have_random_key(yandex_order_id)
                
                if not all_have_random_key:
                    print(f"[Auto-Send Activations] Order {yandex_order_id}: Skipping - requires manual activation keys for: {', '.join(products_with_manual_key)}")
                    continue
                
                # Check if all digital products have activation keys assigned
                all_fulfilled = order_service._check_all_digital_products_fulfilled(yandex_order_id)
                
                if not all_fulfilled:
                    print(f"[Auto-Send Activations] Order {yandex_order_id}: Not all digital products have activation keys assigned")
                    # Try to auto-fulfill missing orders (only if auto-activation is enabled)
                    # Note: app_settings is already checked at the beginning of this function
                    for order in order_group:
                        product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
                        if product and product.product_type == models.ProductType.DIGITAL and not order.activation_key_id:
                            print(f"[Auto-Send Activations] Auto-fulfilling order {yandex_order_id} for product {product.name}")
                            order_service.auto_fulfill_order(order)
                            db.commit()
                    # Re-check after auto-fulfillment
                    all_fulfilled = order_service._check_all_digital_products_fulfilled(yandex_order_id)
                    if not all_fulfilled:
                        print(f"[Auto-Send Activations] Order {yandex_order_id}: Still missing activation keys after auto-fulfillment")
                        continue
                
                # Check if activation codes have already been sent (avoid duplicates)
                already_sent = any(o.activation_code_sent for o in order_group)
                if already_sent:
                    print(f"[Auto-Send Activations] Order {yandex_order_id}: Activation codes already sent, skipping")
                    continue
                
                # All conditions met - send activation for all items
                print(f"[Auto-Send Activations] Order {yandex_order_id}: All conditions met, sending activations...")
                result = order_service.complete_order_with_all_items(order_group)
                
                if result.get("success"):
                    activations_sent += 1
                    print(f"[Auto-Send Activations] ✅ Successfully sent activations for order {yandex_order_id}")
                else:
                    print(f"[Auto-Send Activations] ⚠️  Failed to send activations for order {yandex_order_id}: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(f"[Auto-Send Activations] ⚠️  Error processing order {yandex_order_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        if activations_sent > 0:
            print(f"[Auto-Send Activations] ✅ Automatically sent activations for {activations_sent} order(s)")
        else:
            print(f"[Auto-Send Activations] No activations were sent (orders may be missing templates or activation keys)")
            
    except Exception as e:
        print(f"[Auto-Send Activations] ⚠️  Error in auto-send activations: {str(e)}")
        import traceback
        traceback.print_exc()


def _sync_orders_sync():
    """Synchronous order sync function - pulls orders from Yandex Market"""
    try:
        db = SessionLocal()
        try:
            yandex_api = YandexMarketAPI()
            yandex_orders = yandex_api.get_orders()
            
            orders_created = 0
            orders_updated = 0
            
            for yandex_order in yandex_orders:
                try:
                    yandex_order_id = str(yandex_order.get("id"))
                    
                    # Check if order already exists
                    existing_order = db.query(models.Order).filter(
                        models.Order.yandex_order_id == yandex_order_id
                    ).first()
                    
                    if existing_order:
                        # Update ALL order records with the same yandex_order_id (one record per item)
                        all_orders = db.query(models.Order).filter(
                            models.Order.yandex_order_id == yandex_order_id
                        ).all()
                        
                        # Get all product IDs that already have order records
                        existing_product_ids = {o.product_id for o in all_orders}
                        
                        new_yandex_status = yandex_order.get("status", "")
                        if new_yandex_status:
                            # Map status
                            status_mapping = {
                                "PROCESSING": models.OrderStatus.PROCESSING,
                                "DELIVERY": models.OrderStatus.PROCESSING,
                                "DELIVERED": models.OrderStatus.COMPLETED,
                                "CANCELLED": models.OrderStatus.CANCELLED,
                                "CANCELLED_IN_PROCESSING": models.OrderStatus.CANCELLED,
                                "CANCELLED_IN_DELIVERY": models.OrderStatus.CANCELLED,
                                "PENDING": models.OrderStatus.PENDING,
                                "UNPAID": models.OrderStatus.PENDING,
                                "RESERVED": models.OrderStatus.PENDING,
                            }
                            mapped_status = status_mapping.get(new_yandex_status, models.OrderStatus.PENDING)
                            
                            # Update all existing order records
                            for order_record in all_orders:
                                # Always update yandex_order_data to ensure it has latest items
                                order_record.yandex_order_data = yandex_order
                                
                                if order_record.yandex_status != new_yandex_status:
                                    order_record.yandex_status = new_yandex_status
                                    
                                    # CRITICAL: Never override FINISHED status except with CANCELLED
                                    # FINISHED is a manual override that takes precedence over all Yandex API statuses
                                    if order_record.status == models.OrderStatus.FINISHED:
                                        # Only allow CANCELLED to override FINISHED
                                        if mapped_status == models.OrderStatus.CANCELLED:
                                            order_record.status = mapped_status
                                            print(f"  ⚠️  Order {yandex_order_id}: FINISHED status overridden by CANCELLED from Yandex")
                                        else:
                                            # Keep FINISHED status, don't update from Yandex API
                                            print(f"  ℹ️  Order {yandex_order_id}: Keeping FINISHED status (Yandex status: {new_yandex_status} ignored)")
                                            continue  # Skip status update for this order
                                    else:
                                        # Not FINISHED, update status normally
                                        order_record.status = mapped_status
                                        
                                        # Update item-specific total from items array
                                        items = yandex_order.get("items", [])
                                        if items:
                                            product = db.query(models.Product).filter(
                                                models.Product.id == order_record.product_id
                                            ).first()
                                            if product:
                                                for item in items:
                                                    item_offer_id = item.get("offerId") or item.get("shopSku")
                                                    if item_offer_id == product.yandex_market_id or item_offer_id == product.yandex_market_sku:
                                                        item_price = item.get("price") or item.get("buyerPrice") or 0
                                                        item_count = item.get("count", 1)
                                                        order_record.total_amount = float(item_price) * item_count
                                                        break
                                        
                                        orders_updated += 1
                                else:
                                    # Status didn't change, but still update item-specific total
                                    items = yandex_order.get("items", [])
                                    if items:
                                        product = db.query(models.Product).filter(
                                            models.Product.id == order_record.product_id
                                        ).first()
                                        if product:
                                            for item in items:
                                                item_offer_id = item.get("offerId") or item.get("shopSku")
                                                if item_offer_id == product.yandex_market_id or item_offer_id == product.yandex_market_sku:
                                                    item_price = item.get("price") or item.get("buyerPrice") or 0
                                                    item_count = item.get("count", 1)
                                                    new_total = float(item_price) * item_count
                                                    if order_record.total_amount != new_total:
                                                        order_record.total_amount = new_total
                                                        orders_updated += 1
                                                    break
                            
                            # Auto-complete DELIVERED orders: If Yandex status is DELIVERED and activation codes are sent, mark as completed
                            # BUT: Never override FINISHED status
                            if new_yandex_status == "DELIVERED":
                                # Check if all order records have activation codes sent
                                all_have_activation_sent = all(o.activation_code_sent for o in all_orders)
                                if all_have_activation_sent:
                                    # Mark all as completed (but not if already FINISHED)
                                    for order_record in all_orders:
                                        # Never override FINISHED status
                                        if order_record.status != models.OrderStatus.FINISHED and order_record.status != models.OrderStatus.COMPLETED:
                                            order_record.status = models.OrderStatus.COMPLETED
                                            if not order_record.completed_at:
                                                order_record.completed_at = datetime.utcnow()
                                            orders_updated += 1
                                    print(f"  ✅ Auto-completed order {yandex_order_id} (Yandex status: DELIVERED, activation codes already sent)")
                            
                            # Ensure digital products with COMPLETED or FINISHED status show as sent
                            _ensure_digital_products_marked_as_sent(all_orders, db)
                            
                            # Check for new items in Yandex order that don't have order records yet
                            items = yandex_order.get("items", [])
                            for item in items:
                                offer_id = item.get("offerId") or item.get("shopSku")
                                if not offer_id:
                                    continue
                                
                                # Try to find product
                                product = db.query(models.Product).filter(
                                    (models.Product.yandex_market_id == offer_id) |
                                    (models.Product.yandex_market_id == item.get("shopSku")) |
                                    (models.Product.yandex_market_sku == offer_id) |
                                    (models.Product.yandex_market_sku == item.get("shopSku"))
                                ).first()
                                
                                # Only create order record if product exists and doesn't have one yet
                                if product and product.id not in existing_product_ids:
                                    # Extract buyer info
                                    buyer = yandex_order.get("buyer", {})
                                    buyer_name = None
                                    if isinstance(buyer, dict):
                                        first_name = buyer.get("firstName", "")
                                        last_name = buyer.get("lastName", "")
                                        buyer_name = f"{first_name} {last_name}".strip() or None
                                    
                                    item_price = item.get("price") or item.get("buyerPrice") or 0
                                    item_count = item.get("count", 1)
                                    item_total = float(item_price) * item_count
                                    
                                    new_order = models.Order(
                                        yandex_order_id=yandex_order_id,
                                        product_id=product.id,
                                        customer_name=buyer_name,
                                        customer_email=None,
                                        customer_phone=None,
                                        quantity=item_count,
                                        total_amount=item_total,
                                        status=mapped_status,
                                        yandex_status=new_yandex_status,
                                        yandex_order_data=yandex_order,
                                    )
                                    db.add(new_order)
                                    db.flush()
                                    
                                    # Auto-fulfill digital products (only if auto-activation is enabled)
                                    if product.product_type == models.ProductType.DIGITAL:
                                        app_settings = db.query(models.AppSettings).first()
                                        if app_settings and app_settings.auto_activation_enabled:
                                            from app.services.order_service import OrderService
                                            order_service = OrderService(db)
                                            order_service.auto_fulfill_order(new_order)
                                    
                                    orders_created += 1
                                    existing_product_ids.add(product.id)  # Mark as processed
                                    print(f"  ✅ Created missing order record for product {product.id} ({product.name}) in order {yandex_order_id}")
                    else:
                        # Parse and create new orders from items - Yandex API is source of truth
                        # Create ONE Order record per item in the Yandex order
                        parsed_orders = _parse_yandex_order(yandex_order, db)
                        
                        if not parsed_orders:
                            items = yandex_order.get("items", [])
                            print(f"  ⚠️  Order {yandex_order_id} has {len(items)} items but no products matched in database")
                            print(f"      Items: {[item.get('offerId') or item.get('shopSku') for item in items]}")
                        
                        for new_order, product in parsed_orders:
                            # Check if this order record already exists (composite unique: yandex_order_id + product_id)
                            existing = db.query(models.Order).filter(
                                models.Order.yandex_order_id == new_order.yandex_order_id,
                                models.Order.product_id == new_order.product_id
                            ).first()
                            
                            if existing:
                                # Update existing order record
                                existing.status = new_order.status
                                existing.yandex_status = new_order.yandex_status
                                existing.yandex_order_data = new_order.yandex_order_data
                                existing.quantity = new_order.quantity
                                existing.total_amount = new_order.total_amount
                                existing.customer_name = new_order.customer_name
                                orders_updated += 1
                                print(f"  ✅ Updated existing order record for product {product.id} ({product.name}) in order {yandex_order_id}")
                            else:
                                # Create new order record
                                db.add(new_order)
                                db.flush()  # Get the order ID
                                
                                # Auto-fulfill digital products (only if auto-activation is enabled)
                                if product.product_type == models.ProductType.DIGITAL:
                                    app_settings = db.query(models.AppSettings).first()
                                    if app_settings and app_settings.auto_activation_enabled:
                                        from app.services.order_service import OrderService
                                        order_service = OrderService(db)
                                        order_service.auto_fulfill_order(new_order)
                                
                                orders_created += 1
                                print(f"  ✅ Created order record for product {product.id} ({product.name}) in order {yandex_order_id}")
                except Exception as e:
                    print(f"  ⚠️  Error processing order: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            db.commit()
            print(f"[Auto-Sync] Orders synced at {datetime.utcnow()} - Created: {orders_created}, Updated: {orders_updated}")
            
            # After syncing orders, check for existing orders with activation templates
            # and automatically send activations if all conditions are met
            _auto_send_activations_for_existing_orders(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[Auto-Sync] Error syncing orders: {str(e)}")
        import traceback
        traceback.print_exc()

async def auto_sync_products():
    """Automatically sync products from Yandex Market (async wrapper)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, _sync_products_sync)

async def auto_sync_orders():
    """Automatically sync orders from Yandex Market (async wrapper)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, _sync_orders_sync)

async def periodic_sync():
    """Periodic sync task - runs every 5 minutes"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        await auto_sync_products()
        await auto_sync_orders()


# Business summary functionality removed

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables automatically: {e}")
    
    # Add attachments columns if they don't exist (migration)
    from app.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        # Add column to email_templates
        db.execute(text("""
            ALTER TABLE email_templates 
            ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
        """))
        
        # Add activate_till_days column to email_templates
        db.execute(text("""
            ALTER TABLE email_templates 
            ADD COLUMN IF NOT EXISTS activate_till_days INTEGER DEFAULT 30
        """))
        
        # Add column to marketing_email_templates
        db.execute(text("""
            ALTER TABLE marketing_email_templates 
            ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
        """))
        
        # Add yandex_order_data column to orders table (stores full Yandex order JSON with items[].id)
        db.execute(text("""
            ALTER TABLE orders 
            ADD COLUMN IF NOT EXISTS yandex_order_data JSONB
        """))
        
        # Add yandex_status column to orders table (raw Yandex status string)
        db.execute(text("""
            ALTER TABLE orders 
            ADD COLUMN IF NOT EXISTS yandex_status VARCHAR
        """))
        
        # Add auto_activation_enabled column to app_settings table
        db.execute(text("""
            ALTER TABLE app_settings 
            ADD COLUMN IF NOT EXISTS auto_activation_enabled BOOLEAN DEFAULT FALSE
        """))
        
        # Migration: Remove Telegram columns from app_settings
        try:
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS telegram_bot_token
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS telegram_chat_id
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS notify_new_orders
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS notify_order_status_changes
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS notify_new_reviews
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS notify_review_replies
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS notify_email_broadcasts
            """))
            db.execute(text("""
                ALTER TABLE app_settings 
                DROP COLUMN IF EXISTS notify_new_clients
            """))
            print("✅ Removed Telegram columns from app_settings")
        except Exception as e:
            print(f"⚠️  Warning: Could not remove Telegram columns: {str(e)}")
        
        # Migration: Remove media columns from products
        try:
            db.execute(text("""
                ALTER TABLE products 
                DROP COLUMN IF EXISTS yandex_images
            """))
            db.execute(text("""
                ALTER TABLE products 
                DROP COLUMN IF EXISTS yandex_videos
            """))
            print("✅ Removed media columns from products")
        except Exception as e:
            print(f"⚠️  Warning: Could not remove media columns: {str(e)}")
        
        # Migration: Update orders table to support multiple Order records per Yandex order
        # Remove unique constraint/index on yandex_order_id and add composite unique constraint
        try:
            # Check if the old unique constraint exists
            result = db.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'orders' 
                AND constraint_type = 'UNIQUE' 
                AND constraint_name LIKE '%yandex_order_id%'
            """)).first()
            
            if result:
                # Drop the old unique constraint
                constraint_name = result[0]
                db.execute(text(f"""
                    ALTER TABLE orders 
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                """))
                print(f"✅ Dropped old unique constraint on yandex_order_id: {constraint_name}")
            
            # Also check for unique indexes (not just constraints)
            result = db.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'orders' 
                AND indexname LIKE '%yandex_order_id%'
                AND indexdef LIKE '%UNIQUE%'
            """)).first()
            
            if result:
                # Drop the old unique index
                index_name = result[0]
                db.execute(text(f"""
                    DROP INDEX IF EXISTS {index_name}
                """))
                print(f"✅ Dropped old unique index on yandex_order_id: {index_name}")
            
            # Check if the composite unique constraint already exists
            result = db.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'orders' 
                AND constraint_type = 'UNIQUE' 
                AND constraint_name = 'uq_order_yandex_product'
            """)).first()
            
            if not result:
                # Add composite unique constraint
                db.execute(text("""
                    ALTER TABLE orders 
                    ADD CONSTRAINT uq_order_yandex_product 
                    UNIQUE (yandex_order_id, product_id)
                """))
                print("✅ Added composite unique constraint on (yandex_order_id, product_id)")
            else:
                print("✅ Composite unique constraint already exists")
        except Exception as e:
            print(f"⚠️  Warning: Could not update orders table constraints: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Add FINISHED to orderstatus enum type
        try:
            # First check if the enum value exists
            result = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'finished' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'orderstatus')
                ) as exists;
            """)).first()
            
            if not result or not result[0]:
                # Add the value if it doesn't exist
                # PostgreSQL doesn't support IF NOT EXISTS for ALTER TYPE, so we use a DO block
                db.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_enum 
                            WHERE enumlabel = 'finished' 
                            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'orderstatus')
                        ) THEN
                            ALTER TYPE orderstatus ADD VALUE 'finished';
                        END IF;
                    END $$;
                """))
                db.commit()
                print("✅ Added 'finished' to orderstatus enum")
            else:
                print("✅ 'finished' already exists in orderstatus enum")
        except Exception as e:
            # If enum doesn't exist or already has the value, continue
            print(f"⚠️  Warning: Could not add 'finished' to orderstatus enum: {str(e)}")
            print(f"Note: Could not add 'finished' to orderstatus enum: {e}")
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: Could not run migrations: {e}")
    finally:
        db.close()
    
    # Create default email template and settings
    try:
        create_default_email_template()
    except Exception:
        pass
    try:
        from app.initial_data import create_default_settings
        create_default_settings()
    except Exception:
        pass
    
    # Initial sync on startup - Products first, then orders (orders depend on products)
    print("[Startup] Performing initial sync from Yandex Market...")
    print("[Startup] Step 1: Syncing products...")
    await auto_sync_products()
    await asyncio.sleep(2)  # Small delay to ensure products are committed to database
    print("[Startup] Step 2: Syncing orders...")
    await auto_sync_orders()
    
    # Start periodic sync task
    sync_task = asyncio.create_task(periodic_sync())
    
    # Start review checker task
    review_checker_task = asyncio.create_task(review_checker.start_periodic_check(interval_minutes=15))
    
    # Business summary task removed
    
    yield
    
    # Shutdown
    sync_task.cancel()
    review_checker_task.cancel()
    # Business summary task removed
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    try:
        await review_checker_task
    except asyncio.CancelledError:
        pass
    # Business summary task removed

app = FastAPI(
    title="Yandex Market Digital Products Manager",
    description="Complete ecosystem for managing digital products on Yandex Market",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1",
        "*"  # Allow all origins in development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(activation_templates.router, prefix="/api/activation-templates", tags=["activation-templates"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(marketing_emails.router, prefix="/api/marketing-emails", tags=["marketing-emails"])
app.include_router(documentations.router, prefix="/api/documentations", tags=["documentations"])


@app.get("/")
async def root():
    return {"message": "Yandex Market Digital Products Manager API"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
