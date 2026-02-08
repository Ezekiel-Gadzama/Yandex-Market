from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_ as sql_or
from typing import List
import json
from app.database import get_db
from app import models, schemas
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


def _convert_product_json_fields(product: models.Product) -> dict:
    """Convert product to API response - only essential local fields and yandex_full_data"""
    product_dict = {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "product_type": product.product_type,
        "cost_price": product.cost_price,
        "selling_price": product.selling_price,
        "supplier_url": product.supplier_url,
        "supplier_name": product.supplier_name,
        "yandex_market_id": product.yandex_market_id,
        "yandex_market_sku": product.yandex_market_sku,
        "email_template_id": product.email_template_id,
        "documentation_id": product.documentation_id,
        "is_active": product.is_active,
        "is_synced": product.is_synced,
        "profit": product.profit,
        "profit_percentage": product.profit_percentage,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        # Full Yandex JSON data (all Yandex fields are stored here)
        "yandex_full_data": product.yandex_full_data,
    }
    
    return product_dict


@router.get("/", response_model=List[schemas.Product])
def get_products(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    product_type: str = None,
    search: str = Query(None, description="Search by name, description, or activation key"),
    db: Session = Depends(get_db)
):
    """Get all products with optional filters"""
    query = db.query(models.Product)
    
    if is_active is not None:
        query = query.filter(models.Product.is_active == is_active)
    
    if product_type:
        query = query.filter(models.Product.product_type == product_type)
    
    # Search by name, description, or generated keys
    if search:
        search_term = f"%{search.lower()}%"
        # Search in name and description
        from sqlalchemy import func
        filters = [func.lower(models.Product.name).like(search_term)]
        # Only add description filter if description column exists and is not None
        filters.append(func.lower(models.Product.description).like(search_term))
        name_desc_filter = sql_or(*filters)
        
        # Search in generated_keys
        # We need to check if any key in the JSON array matches
        matching_product_ids = []
        all_products = db.query(models.Product).all()
        for p in all_products:
            if p.generated_keys:
                try:
                    keys_list = json.loads(p.generated_keys) if isinstance(p.generated_keys, str) else p.generated_keys
                    if isinstance(keys_list, list):
                        for key_entry in keys_list:
                            if isinstance(key_entry, dict) and key_entry.get('key', '').lower().find(search.lower()) != -1:
                                matching_product_ids.append(p.id)
                                break
                            elif isinstance(key_entry, str) and key_entry.lower().find(search.lower()) != -1:
                                matching_product_ids.append(p.id)
                                break
                except:
                    pass
        
        if matching_product_ids:
            query = query.filter(sql_or(name_desc_filter, models.Product.id.in_(matching_product_ids)))
        else:
            query = query.filter(name_desc_filter)
    
    products = query.offset(skip).limit(limit).all()
    return [_convert_product_json_fields(p) for p in products]


@router.get("/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _convert_product_json_fields(product)


@router.get("/{product_id}/full", response_model=dict)
def get_product_full_details(product_id: int, db: Session = Depends(get_db)):
    """Get full product details including all fields and media"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get full product data
    product_dict = _convert_product_json_fields(product)
    
    # Include stored Yandex full data if available
    if product.yandex_full_data:
        product_dict["yandex_full_data"] = product.yandex_full_data
        
        # Always try to refresh product card data to get latest media and details
        if product.is_synced and product.yandex_market_id:
            try:
                yandex_api = YandexMarketAPI()
                product_card = yandex_api.get_product_card(product.yandex_market_id)
                if product_card:
                    # Merge product card data with existing yandex_full_data
                    import copy
                    from app.routers.sync import _is_digital_product
                    merged_data = copy.deepcopy(product.yandex_full_data)
                    # Update with product card data (product card takes precedence for detailed fields)
                    merged_data.update(product_card)
                    product.yandex_full_data = merged_data
                    product_dict["yandex_full_data"] = merged_data
                    
                    # Update product type based on product card data
                    is_digital = _is_digital_product(merged_data)
                    product.product_type = models.ProductType.DIGITAL if is_digital else models.ProductType.PHYSICAL
                    product_dict["product_type"] = product.product_type.value
                    
                    # Update product name from mapping.marketSkuName if available
                    if product_card.get("mapping", {}).get("marketSkuName"):
                        product.name = product_card["mapping"]["marketSkuName"]
                        product_dict["name"] = product_card["mapping"]["marketSkuName"]
                    
                    db.commit()
                    print(f"✅ Successfully refreshed product card for {product.yandex_market_id} (type: {'digital' if is_digital else 'physical'})")
            except Exception as e:
                print(f"⚠️  Warning: Could not refresh product card: {str(e)}")
                # Continue with existing data if card fetch fails
    elif product.is_synced and product.yandex_market_id:
        # Fallback: try to get from API if not stored locally
        try:
            yandex_api = YandexMarketAPI()
            yandex_products = yandex_api.get_products()
            
            # Find matching product in Yandex
            for yandex_product in yandex_products:
                if (yandex_product.get("id") == product.yandex_market_id or 
                    yandex_product.get("sku") == product.yandex_market_sku):
                    # Log the raw Yandex product data for this specific product
                    import json
                    print("=" * 80)
                    print(f"RAW YANDEX API RESPONSE FOR PRODUCT {product.yandex_market_id}:")
                    print("=" * 80)
                    print(json.dumps(yandex_product, indent=2, ensure_ascii=False))
                    print("=" * 80)
                    
                    # Store basic offer data first
                    product.yandex_full_data = yandex_product
                    product_dict["yandex_full_data"] = yandex_product
                    db.commit()
                    break
            
            # Also fetch full product card details (name, description, images, videos, characteristics)
            if product.yandex_market_id:
                try:
                    product_card = yandex_api.get_product_card(product.yandex_market_id)
                    if product_card:
                        # Merge product card data with existing yandex_full_data
                        if product.yandex_full_data:
                            # Deep merge to preserve existing data
                            import copy
                            merged_data = copy.deepcopy(product.yandex_full_data)
                            # Update with product card data (product card takes precedence for detailed fields)
                            merged_data.update(product_card)
                            product.yandex_full_data = merged_data
                            product_dict["yandex_full_data"] = merged_data
                        else:
                            product.yandex_full_data = product_card
                            product_dict["yandex_full_data"] = product_card
                        db.commit()
                        print(f"✅ Successfully fetched and merged product card for {product.yandex_market_id}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not fetch product card: {str(e)}")
                    # Continue with basic offer data if card fetch fails
        except Exception as e:
            # If Yandex API fails, just return local data
            print(f"Failed to get Yandex product details: {str(e)}")
    
    return product_dict


@router.put("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a product from admin dashboard
    
    Process:
    1. Update local database
    2. If product is synced with Yandex, push changes to Yandex
    3. Immediately sync back from Yandex to get confirmed values
    4. Result: Local and Yandex have the same values
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product is synced with Yandex
    is_synced = db_product.is_synced and db_product.yandex_market_id is not None
    
    # Update local database first
    update_data = product_update.dict(exclude_unset=True)
    
    # Handle dynamic field updates from Yandex JSON
    yandex_field_updates = update_data.pop("yandex_field_updates", None)
    has_yandex_updates = yandex_field_updates and len(yandex_field_updates) > 0
    
    if has_yandex_updates and db_product.yandex_full_data:
        # Update the stored Yandex JSON with new values
        if isinstance(db_product.yandex_full_data, dict):
            db_product.yandex_full_data.update(yandex_field_updates)
        else:
            db_product.yandex_full_data = yandex_field_updates
    
    # Update only local-only fields (cost_price, supplier info, email_template_id, documentation_id, is_active)
    local_only_fields = ['cost_price', 'supplier_url', 'supplier_name', 'email_template_id', 'documentation_id', 'is_active']
    for field in local_only_fields:
        if field in update_data:
            setattr(db_product, field, update_data[field])
    
    # If product is synced with Yandex and we have Yandex field updates, push changes
    if is_synced and has_yandex_updates:
        try:
            yandex_api = YandexMarketAPI()
            
            # Step 1: Push updates to Yandex using yandex_field_updates
            yandex_api.update_product(db_product, field_updates=yandex_field_updates)
            
            # Step 2: Sync back from Yandex to get confirmed values
            yandex_products = yandex_api.get_products()
            for yandex_product in yandex_products:
                if (yandex_product.get("id") == db_product.yandex_market_id or 
                    yandex_product.get("sku") == db_product.yandex_market_sku):
                    # Preserve local-only fields
                    preserved_cost_price = db_product.cost_price
                    preserved_supplier_url = db_product.supplier_url
                    preserved_supplier_name = db_product.supplier_name
                    preserved_email_template_id = db_product.email_template_id
                    preserved_documentation_id = db_product.documentation_id
                    
                    # Update yandex_full_data with latest from Yandex (merge our updates)
                    if isinstance(db_product.yandex_full_data, dict):
                        # Merge Yandex response with our updates
                        db_product.yandex_full_data = {**yandex_product, **yandex_field_updates}
                    else:
                        db_product.yandex_full_data = {**yandex_product, **yandex_field_updates}
                    
                    # Update basic fields from Yandex
                    db_product.name = yandex_product.get("name", db_product.name)
                    db_product.description = yandex_product.get("description", db_product.description)
                    db_product.selling_price = yandex_product.get("price", db_product.selling_price)
                    
                    # Restore preserved local-only fields
                    db_product.cost_price = preserved_cost_price
                    db_product.supplier_url = preserved_supplier_url
                    db_product.supplier_name = preserved_supplier_name
                    db_product.email_template_id = preserved_email_template_id
                    db_product.documentation_id = preserved_documentation_id
                    
                    db_product.is_synced = True
                    break
        except Exception as e:
            # If Yandex update fails, still save local changes but mark as not synced
            db_product.is_synced = False
            db.commit()
            db.refresh(db_product)
            raise HTTPException(
                status_code=500, 
                detail=f"Product updated locally but failed to sync to Yandex: {str(e)}"
            )
    
    db.commit()
    db.refresh(db_product)
    return _convert_product_json_fields(db_product)


@router.get("/{product_id}/analytics", response_model=schemas.ProductAnalytics)
def get_product_analytics(product_id: int, db: Session = Depends(get_db)):
    """Get analytics for a specific product"""
    from sqlalchemy import func
    from datetime import datetime
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get all orders for this product
    orders = db.query(models.Order).filter(models.Order.product_id == product_id).all()
    completed_orders = [o for o in orders if o.status == models.OrderStatus.COMPLETED]
    
    # Calculate metrics
    total_orders = len(orders)
    completed_count = len(completed_orders)
    total_revenue = sum(o.total_amount for o in completed_orders)
    total_profit = sum(o.profit for o in completed_orders)
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    average_order_value = total_revenue / completed_count if completed_count > 0 else 0
    
    return schemas.ProductAnalytics(
        product_id=product.id,
        product_name=product.name,
        total_orders=total_orders,
        completed_orders=completed_count,
        total_revenue=total_revenue,
        total_profit=total_profit,
        profit_margin=profit_margin,
        average_order_value=average_order_value,
        period_start=None,
        period_end=None
    )


# upload_product_to_yandex removed - products can only be synced from Yandex Market


@router.post("/{product_id}/generate-keys", response_model=dict)
def generate_activation_keys(
    product_id: int,
    count: int = 10,
    db: Session = Depends(get_db)
):
    """Generate activation keys for a product"""
    import json
    from datetime import datetime
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.product_type != models.ProductType.DIGITAL:
        raise HTTPException(status_code=400, detail="Only digital products can have activation keys")
    
    import secrets
    keys_created = []
    generated_keys_list = []
    
    # Get existing generated_keys from product
    existing_keys = []
    if product.generated_keys:
        try:
            existing_keys = json.loads(product.generated_keys) if isinstance(product.generated_keys, str) else product.generated_keys
        except:
            existing_keys = []
    
    for _ in range(count):
        # Generate a unique key
        key = f"{product.yandex_market_sku or product.id}-{secrets.token_urlsafe(16)}"
        
        # Check if key already exists in ActivationKey table
        existing = db.query(models.ActivationKey).filter(models.ActivationKey.key == key).first()
        if existing:
            continue
        
        # Check if key already exists in product.generated_keys
        if any(k.get('key') == key for k in existing_keys):
            continue
        
        activation_key = models.ActivationKey(
            product_id=product_id,
            key=key
        )
        db.add(activation_key)
        keys_created.append(key)
        
        # Add to generated_keys list
        generated_keys_list.append({
            "key": key,
            "timestamp": datetime.utcnow().isoformat(),
            "order_id": None  # Will be updated when used
        })
    
    # Update product.generated_keys with new keys
    all_keys = existing_keys + generated_keys_list
    product.generated_keys = json.dumps(all_keys)
    
    db.commit()
    return {"success": True, "keys_created": len(keys_created), "keys": keys_created}
