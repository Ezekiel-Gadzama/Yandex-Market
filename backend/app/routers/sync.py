from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
import json
from app.database import get_db
from app import models, schemas
from app.services.yandex_api import YandexMarketAPI
from app.auth import get_current_active_user, get_business_id
from app.services.config_validator import ConfigurationError, format_config_error_response

router = APIRouter()


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


@router.post("/", response_model=schemas.SyncResult)
def sync_all(
    force: bool = False,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sync all data FROM Yandex Market TO local database (one-way sync)
    
    This syncs both products and orders.
    - force=True: Syncs all items even if already synced
    - force=False: Only syncs items that aren't already synced
    """
    try:
        # Sync products
        products_result = sync_products(force=force, current_user=current_user, db=db)
        
        # Sync orders
        orders_result = sync_orders(current_user=current_user, db=db)
        
        return schemas.SyncResult(
            success=True,
            products_synced=products_result.products_synced,
            products_created=products_result.products_created,
            products_updated=products_result.products_updated,
            products_pushed=0,
            errors=products_result.errors
        )
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_config_error_response(e)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/products", response_model=schemas.SyncResult)
def sync_products(
    force: bool = False,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sync products FROM Yandex Market TO local database (one-way sync)
    
    Yandex Market is the source of truth. This sync:
    - Pulls all products from Yandex Market
    - Updates local database to match Yandex exactly
    - Preserves only local-only fields (cost_price, supplier info) that don't exist in Yandex
    """
    try:
        from app.auth import get_business_id
        from app.services.config_validator import ConfigurationError, format_config_error_response
        
        business_id = get_business_id(current_user)
        yandex_api = YandexMarketAPI(business_id=business_id, db=db)
        yandex_products = yandex_api.get_products()
        
        products_synced = 0
        products_created = 0
        products_updated = 0
        errors = []
        
        for yandex_product in yandex_products:
            try:
                # Extract offer ID (can be in different fields)
                yandex_id = (
                    yandex_product.get("offerId") or
                    yandex_product.get("id") or
                    yandex_product.get("shopSku") or
                    yandex_product.get("sku")
                )
                
                if not yandex_id:
                    errors.append(f"Product missing offerId: {json.dumps(yandex_product)}")
                    continue
                
                yandex_sku = (
                    yandex_product.get("shopSku") or
                    yandex_product.get("sku") or
                    yandex_id
                )
                
                # Check if product already exists for this business
                # Also check for products without business_id (legacy) and update them
                existing_product = db.query(models.Product).filter(
                    (models.Product.business_id == business_id) |
                    (models.Product.business_id.is_(None))
                ).filter(
                    (models.Product.yandex_market_id == yandex_id) |
                    (models.Product.yandex_market_sku == yandex_sku)
                ).first()
                
                # If we found a product without business_id, update it
                if existing_product and existing_product.business_id is None:
                    existing_product.business_id = business_id
                    db.flush()  # Flush to ensure business_id is set before continuing
                
                if existing_product:
                    if not force and existing_product.is_synced:
                        products_synced += 1
                        continue
                    
                    # Preserve local-only fields before updating
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
                    
                    # Restore preserved local-only fields (these are never synced from Yandex)
                    existing_product.cost_price = preserved_cost_price
                    existing_product.supplier_url = preserved_supplier_url
                    existing_product.supplier_name = preserved_supplier_name
                    existing_product.email_template_id = preserved_email_template_id
                    existing_product.documentation_id = preserved_documentation_id
                    
                    existing_product.is_synced = True
                    products_updated += 1
                    print(f"  ✅ Updated existing product: {product_name} (offerId: {yandex_id}, type: {'digital' if is_digital else 'physical'})")
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
                        # Continue with basic offer data if card fetch fails
                    
                    # Determine product type from Yandex data
                    is_digital = _is_digital_product(yandex_product)
                    
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
                    is_active = True
                    status = yandex_product.get("status", "")
                    if status:
                        # PUBLISHED = active, others = inactive
                        is_active = (status == "PUBLISHED")
                    elif "available" in yandex_product:
                        is_active = bool(yandex_product.get("available"))
                    
                    new_product = models.Product(
                        name=product_name,
                        description=yandex_product.get("description"),
                        yandex_market_id=yandex_id,
                        yandex_market_sku=yandex_sku,
                        selling_price=selling_price,
                        cost_price=0,  # Will need to be set manually
                        is_synced=True,
                        product_type=models.ProductType.DIGITAL if is_digital else models.ProductType.PHYSICAL,
                        is_active=is_active,
                        yandex_full_data=yandex_product,  # Store complete Yandex JSON (includes product card data)
                        business_id=business_id  # Set business_id for multi-tenancy
                    )
                    
                    print(f"  ✅ Created new product: {product_name} (offerId: {yandex_id}, type: {'digital' if is_digital else 'physical'}, price: {selling_price})")
                    
                    db.add(new_product)
                    products_created += 1
                
                products_synced += 1
            except Exception as e:
                errors.append(f"Error syncing product {yandex_product.get('id')}: {str(e)}")
        
        db.commit()
        
        return schemas.SyncResult(
            success=True,
            products_synced=products_synced,
            products_created=products_created,
            products_updated=products_updated,
            products_pushed=0,  # Sync is one-way: Yandex → Local
            errors=errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/orders", response_model=dict)
def sync_orders(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync orders from Yandex Market"""
    from app.services.yandex_api import YandexMarketAPI
    from app.main import _parse_yandex_order
    from app.services.order_service import OrderService
    
    try:
        business_id = get_business_id(current_user)
        yandex_api = YandexMarketAPI(business_id=business_id, db=db)
        orders_data = yandex_api.get_orders()
        
        orders_created = 0
        orders_updated = 0
        
        # Handle different response structures
        if "orders" in orders_data:
            orders_list = orders_data["orders"]
        elif isinstance(orders_data, list):
            orders_list = orders_data
        else:
            orders_list = [orders_data]
        
        for order_data in orders_list:
            try:
                parsed_orders = _parse_yandex_order(order_data, db, business_id=business_id)
                
                for new_order, product in parsed_orders:
                    # Check if order already exists for this business
                    existing = db.query(models.Order).filter(
                        models.Order.business_id == business_id,
                        models.Order.yandex_order_id == new_order.yandex_order_id,
                        models.Order.product_id == new_order.product_id
                    ).first()
                    
                    if existing:
                        orders_updated += 1
                    else:
                        db.add(new_order)
                        orders_created += 1
                        
                        # Auto-fulfill digital products
                        if product.product_type == models.ProductType.DIGITAL:
                            order_service = OrderService(db, business_id=business_id)
                            order_service.auto_fulfill_order(new_order)
                
            except Exception as e:
                print(f"Error processing order: {str(e)}")
                continue
        
        db.commit()
        
        # After syncing orders, check for existing orders with activation templates
        # and automatically send activations if all conditions are met
        from app.main import _auto_send_activations_for_existing_orders
        _auto_send_activations_for_existing_orders(db)
        
        return {
            "success": True,
            "orders_created": orders_created,
            "orders_updated": orders_updated
        }
    except ConfigurationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_config_error_response(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Order sync failed: {str(e)}")
