from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.database import get_db
from app import models, schemas
from app.services.order_service import OrderService
from app.auth import get_current_active_user, get_business_id

router = APIRouter()


@router.get("/", response_model=List[schemas.Order])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    refresh_status: bool = True,  # Optionally refresh order status from Yandex
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all orders with optional filters. Only returns orders for the current user's business.
    
    Orders are grouped by yandex_order_id. Each order group contains all items/products.
    
    If refresh_status is True, will fetch fresh order status from Yandex API for orders
    that are in PROCESSING status to check if they've been DELIVERED.
    """
    from datetime import datetime
    from app.services.yandex_api import YandexMarketAPI
    from app.config import settings
    
    business_id = get_business_id(current_user)
    query = db.query(models.Order).filter(models.Order.business_id == business_id)
    
    if status:
        # Special handling for "unfinished" filter - show all orders that are not finished
        if status.lower() == "unfinished":
            query = query.filter(models.Order.status != models.OrderStatus.FINISHED)
        else:
            # Convert string status to enum for comparison
            status_upper = status.upper()
            try:
                status_enum = models.OrderStatus[status_upper]
                query = query.filter(models.Order.status == status_enum)
            except KeyError:
                # Invalid status, ignore filter
                pass
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(models.Order.created_at >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(models.Order.created_at <= end_dt)
        except:
            pass
    
    orders = query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit * 10).all()  # Get more to account for grouping
    
    # Refresh order status from Yandex for orders that might be stale
    if refresh_status:
        try:
            from app.services.config_validator import ConfigurationError, format_config_error_response
            yandex_api = YandexMarketAPI(business_id=business_id, db=db)
            unique_yandex_order_ids = set()
            orders_to_refresh = []
            
            # Collect unique order IDs that need refreshing
            for order in orders:
                yandex_id = order.yandex_order_id
                if yandex_id and yandex_id not in unique_yandex_order_ids:
                    unique_yandex_order_ids.add(yandex_id)
                    # Only refresh if order is in PROCESSING status (might have been delivered)
                    # or if yandex_status is missing/old
                    # NEVER refresh FINISHED orders - they are manually overridden and should not be updated
                    if (order.status != models.OrderStatus.FINISHED and 
                        (order.status == models.OrderStatus.PROCESSING or 
                         order.yandex_status in ["PROCESSING", None, ""])):
                        orders_to_refresh.append(yandex_id)
            
            # Refresh orders in batch (limit to avoid too many API calls)
            for yandex_id in orders_to_refresh[:10]:  # Limit to 10 refreshes per request
                try:
                    print(f"🔄 Refreshing order status from Yandex for order {yandex_id}")
                    fresh_order_data = yandex_api.get_order(str(yandex_id))
                    
                    # Extract status from fresh data
                    fresh_status = fresh_order_data.get("status")
                    if fresh_status:
                        # Update all order records with this yandex_order_id (filter by business_id)
                        all_orders_for_id = db.query(models.Order).filter(
                            models.Order.yandex_order_id == yandex_id,
                            models.Order.business_id == business_id
                        ).all()
                        
                        for order_record in all_orders_for_id:
                            # Update yandex_order_data with fresh data
                            order_record.yandex_order_data = fresh_order_data
                            order_record.yandex_status = fresh_status
                            
                            # Only update status if it's not already FINISHED (manual override takes precedence)
                            if order_record.status != models.OrderStatus.FINISHED:
                                # Map Yandex status to our status
                                from app.routers.webhooks import _map_yandex_status
                                mapped_status = _map_yandex_status(fresh_status)
                                order_record.status = mapped_status
                                
                                # Auto-complete if DELIVERED and activation codes are sent
                                # But only if status is not FINISHED (already checked above)
                                if fresh_status == "DELIVERED" and order_record.activation_code_sent:
                                    order_record.status = models.OrderStatus.COMPLETED
                                    if not order_record.completed_at:
                                        order_record.completed_at = datetime.utcnow()
                        
                        db.commit()
                        print(f"✅ Updated order {yandex_id} status to {fresh_status}")
                except Exception as e:
                    print(f"⚠️  Could not refresh order {yandex_id} status: {str(e)}")
                    # Continue with cached data if refresh fails
                    db.rollback()
                    pass
            
            # Re-query orders after refresh to get updated status
            # IMPORTANT: Re-query to get fresh data from database, especially for FINISHED status
            if orders_to_refresh:
                # Rebuild query to get fresh data (filter by business_id)
                fresh_query = db.query(models.Order).filter(models.Order.business_id == business_id)
                if status:
                    if status.lower() == "unfinished":
                        fresh_query = fresh_query.filter(models.Order.status != models.OrderStatus.FINISHED)
                    else:
                        status_upper = status.upper()
                        try:
                            status_enum = models.OrderStatus[status_upper]
                            fresh_query = fresh_query.filter(models.Order.status == status_enum)
                        except KeyError:
                            pass
                if start_date:
                    try:
                        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        fresh_query = fresh_query.filter(models.Order.created_at >= start_dt)
                    except:
                        pass
                if end_date:
                    try:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        fresh_query = fresh_query.filter(models.Order.created_at <= end_dt)
                    except:
                        pass
                orders = fresh_query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit * 10).all()
        except ConfigurationError as e:
            # Configuration error - log but don't fail the request
            print(f"⚠️  Yandex API configuration required: {e.message}")
        except Exception as e:
            print(f"⚠️  Could not initialize Yandex API: {str(e)}")
    
    # Group orders by yandex_order_id
    orders_by_yandex_id = {}
    for order in orders:
        yandex_id = order.yandex_order_id
        if yandex_id not in orders_by_yandex_id:
            orders_by_yandex_id[yandex_id] = []
        orders_by_yandex_id[yandex_id].append(order)
    
    # Build result: one entry per yandex_order_id with all items
    result = []
    seen_yandex_ids = set()
    
    for order in orders:
        yandex_id = order.yandex_order_id
        if yandex_id in seen_yandex_ids:
            continue
        seen_yandex_ids.add(yandex_id)
        
        # Get all orders with this yandex_order_id
        order_group = orders_by_yandex_id[yandex_id]
        
        # Use the first order as the base (they share customer info, dates, etc.)
        # IMPORTANT: Refresh from database to ensure we have the latest status (especially FINISHED)
        base_order = order_group[0]
        db.refresh(base_order)  # Ensure we have the latest status from database
        
        # Get all products in this order
        order_items = []
        total_amount = 0
        all_activation_sent = True  # Check if ALL items have activation sent
        
        # Get yandex_order_data to extract item IDs
        yandex_order_data = base_order.yandex_order_data or {}
        if isinstance(yandex_order_data, str):
            import json
            try:
                yandex_order_data = json.loads(yandex_order_data)
            except:
                yandex_order_data = {}
        
        # Extract items from yandex_order_data
        # Yandex response structure: { "items": [...] } or { "order": { "items": [...] } }
        yandex_items = yandex_order_data.get("items", [])
        if not yandex_items and isinstance(yandex_order_data, dict) and "order" in yandex_order_data:
            yandex_items = yandex_order_data["order"].get("items", [])
        
        # Debug: Log items extraction
        if not yandex_items:
            print(f"⚠️  Warning: Order {base_order.yandex_order_id} has no items in yandex_order_data")
            print(f"   yandex_order_data keys: {list(yandex_order_data.keys()) if isinstance(yandex_order_data, dict) else 'not a dict'}")
        else:
            print(f"✅ Order {base_order.yandex_order_id} has {len(yandex_items)} items in yandex_order_data")
        
        # CRITICAL FIX: Build items array from Yandex items (source of truth), not just database records
        # This ensures ALL products from Yandex are shown, even if some aren't in our database
        processed_yandex_item_ids = set()
        
        # First, process items that have matching order records in database
        for o in order_group:
            # Filter product by business_id to ensure data isolation
            product = db.query(models.Product).filter(
                models.Product.id == o.product_id,
                models.Product.business_id == business_id
            ).first()
            if product:
                # Find matching Yandex item to get item ID
                yandex_item_id = None
                yandex_offer_id = None
                matching_yandex_item = None
                
                for yandex_item in yandex_items:
                    item_offer_id = yandex_item.get("offerId") or yandex_item.get("shopSku")
                    if item_offer_id == product.yandex_market_id or item_offer_id == product.yandex_market_sku:
                        yandex_item_id = yandex_item.get("id")
                        yandex_offer_id = item_offer_id
                        matching_yandex_item = yandex_item
                        processed_yandex_item_ids.add(yandex_item_id)
                        break
                
                # Use price from Yandex item if available, otherwise from order record
                if matching_yandex_item:
                    item_price = float(matching_yandex_item.get("price") or matching_yandex_item.get("buyerPrice") or 0)
                    item_count = matching_yandex_item.get("count", o.quantity)
                    item_total = item_price * item_count
                else:
                    item_price = o.total_amount / o.quantity if o.quantity > 0 else 0
                    item_count = o.quantity
                    item_total = o.total_amount
                
                order_items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item_count,
                    "item_price": item_price,
                    "item_total": item_total,
                    "yandex_item_id": yandex_item_id,
                    "yandex_offer_id": yandex_offer_id,
                    "activation_code_sent": o.activation_code_sent,
                    "activation_key_id": o.activation_key_id,
                    "email_template_id": product.email_template_id,
                    "documentation_id": product.documentation_id,
                })
                total_amount += item_total
                if not o.activation_code_sent:
                    all_activation_sent = False
        
        # Second, process Yandex items that DON'T have matching order records (products not in our database)
        for yandex_item in yandex_items:
            yandex_item_id = yandex_item.get("id")
            if yandex_item_id in processed_yandex_item_ids:
                continue  # Already processed
            
            offer_id = yandex_item.get("offerId") or yandex_item.get("shopSku")
            item_price = float(yandex_item.get("price") or yandex_item.get("buyerPrice") or 0)
            item_count = yandex_item.get("count", 1)
            item_total = item_price * item_count
            item_name = yandex_item.get("offerName") or offer_id or "Unknown Product"
            
            # Try to find product in database (filter by business_id)
            product = db.query(models.Product).filter(
                models.Product.business_id == business_id
            ).filter(
                (models.Product.yandex_market_id == offer_id) |
                (models.Product.yandex_market_id == yandex_item.get("shopSku")) |
                (models.Product.yandex_market_sku == offer_id) |
                (models.Product.yandex_market_sku == yandex_item.get("shopSku"))
            ).first()
            
            if product:
                # Product exists but no order record - this shouldn't happen, but handle it
                order_items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item_count,
                    "item_price": item_price,
                    "item_total": item_total,
                    "yandex_item_id": yandex_item_id,
                    "yandex_offer_id": offer_id,
                    "activation_code_sent": False,  # No order record, so not sent
                    "activation_key_id": None,
                    "email_template_id": product.email_template_id,
                    "documentation_id": product.documentation_id,
                })
            else:
                # Product not in database - show it anyway so user knows it exists in Yandex
                order_items.append({
                    "product_id": None,  # No product in database
                    "product_name": item_name,  # Use Yandex product name
                    "quantity": item_count,
                    "item_price": item_price,
                    "item_total": item_total,
                    "yandex_item_id": yandex_item_id,
                    "yandex_offer_id": offer_id,
                    "activation_code_sent": False,
                    "activation_key_id": None,
                    "email_template_id": None,
                    "documentation_id": None,
                })
            
            total_amount += item_total
            processed_yandex_item_ids.add(yandex_item_id)
            print(f"  ℹ️  Added Yandex item {yandex_item_id} ({item_name}) - product {'found' if product else 'NOT in database'}")
        
        # Convert order_items to OrderItem schema objects
        order_item_objects = [
            schemas.OrderItem(**item) for item in order_items
        ]
        
        # Extract delivery type from yandex_order_data
        delivery_type = None
        delivery_info = yandex_order_data.get("delivery", {})
        if isinstance(delivery_info, dict):
            delivery_type = delivery_info.get("type")  # "DIGITAL" or "DELIVERY"
        
        # Auto-complete DELIVERED orders: If Yandex status is DELIVERED and we've sent activation codes, mark as completed
        # But only if status is not already FINISHED (manual override takes precedence)
        # IMPORTANT: Check this BEFORE building order_dict to ensure we use the correct status
        yandex_status = base_order.yandex_status or ""
        if yandex_status == "DELIVERED" and all_activation_sent and base_order.status != models.OrderStatus.COMPLETED:
            # Only update if status is not FINISHED (manual override takes precedence)
            if base_order.status != models.OrderStatus.FINISHED:
                # Update all order records in this group to COMPLETED
                for o in order_group:
                    o.status = models.OrderStatus.COMPLETED
                    if not o.completed_at:
                        from datetime import datetime
                        o.completed_at = datetime.utcnow()
                db.commit()
                # Refresh base_order to get updated status from database
                db.refresh(base_order)
                print(f"✅ Auto-completed order {base_order.yandex_order_id} (Yandex status: DELIVERED, activation codes already sent)")
        
        # Ensure digital products with COMPLETED or FINISHED status are marked as sent
        # Import here to avoid circular imports
        from app.main import _ensure_digital_products_marked_as_sent
        try:
            _ensure_digital_products_marked_as_sent(order_group, db)
            db.commit()
        except Exception as e:
            print(f"⚠️  Error ensuring digital products marked as sent: {str(e)}")
            db.rollback()
        
        # Check if a client already exists for this order
        # Query clients and check if order_id is in their order_ids array
        has_client = False
        # Use a simple Python check - it's fast enough for most use cases
        # Query all clients for this business and check their order_ids (including empty arrays)
        business_id = get_business_id(current_user)
        all_clients = db.query(models.Client).filter(models.Client.business_id == business_id).all()
        for client in all_clients:
            # Check if order_ids exists and contains the yandex_id
            if client.order_ids is not None:
                # Handle both list and JSONB array formats
                order_ids_list = client.order_ids if isinstance(client.order_ids, list) else []
                if yandex_id in order_ids_list:
                    has_client = True
                    break
        
        # Build order dict with items
        # IMPORTANT: Always use the actual status from database - FINISHED status takes precedence over Yandex API
        # Refresh base_order one more time to ensure we have the absolute latest status from database
        db.refresh(base_order)
        order_dict = {
            **base_order.__dict__,
            "product_name": order_items[0]["product_name"] if order_items else None,  # First product for display
            "total_amount": total_amount,  # Sum of all items
            "items": order_item_objects,  # All products in this order (as OrderItem objects)
            "items_count": len(order_items),  # Number of products
            "activation_code_sent": all_activation_sent,  # True only if ALL items have activation sent
            "delivery_type": delivery_type,  # "DIGITAL" or "DELIVERY"
            "status": base_order.status,  # CRITICAL: Use actual database status (FINISHED takes precedence over everything)
            "has_client": has_client,  # Whether a client already exists for this order
        }
        
        # Convert to Order schema to ensure proper serialization
        order_schema = schemas.Order(**order_dict)
        result.append(order_schema)
        
        # Limit results
        if len(result) >= limit:
            break
    
    return result


@router.get("/{order_id}", response_model=schemas.Order)
def get_order(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a single order by ID"""
    business_id = get_business_id(current_user)
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.business_id == business_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
def create_order(
    order: schemas.OrderCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new order (typically from Yandex Market webhook)"""
    business_id = get_business_id(current_user)
    # Check if order already exists for this business
    existing = db.query(models.Order).filter(
        models.Order.business_id == business_id,
        models.Order.yandex_order_id == order.yandex_order_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Order already exists")
    
    order_data = order.dict()
    order_data['business_id'] = business_id
    db_order = models.Order(**order_data)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Auto-process digital products
    product = db.query(models.Product).filter(
        models.Product.id == db_order.product_id,
        models.Product.business_id == business_id
    ).first()
    if product and product.product_type == models.ProductType.DIGITAL:
        order_service = OrderService(db, business_id=business_id)
        order_service.auto_fulfill_order(db_order)
    
    return db_order


@router.put("/{order_id}", response_model=schemas.Order)
def update_order(
    order_id: int,
    order_update: schemas.OrderUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an order"""
    business_id = get_business_id(current_user)
    db_order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.business_id == business_id
    ).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    db.commit()
    db.refresh(db_order)
    return db_order


@router.post("/{order_id}/fulfill", response_model=dict)
def fulfill_order(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually fulfill an order (assign activation key and send email)"""
    business_id = get_business_id(current_user)
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.business_id == business_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Filter product by business_id to ensure data isolation
    product = db.query(models.Product).filter(
        models.Product.id == order.product_id,
        models.Product.business_id == business_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.product_type != models.ProductType.DIGITAL:
        raise HTTPException(status_code=400, detail="Only digital products can be fulfilled with activation keys")
    
    order_service = OrderService(db, business_id=business_id)
    result = order_service.fulfill_order(order)
    
    return result


@router.post("/{order_id}/complete", response_model=dict)
def complete_order(
    order_id: int,
    body: Optional[Dict[str, Dict[int, str]]] = Body(None),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Complete order by sending activation code to Yandex Market for ALL items in the order
    
    Args:
        order_id: The order ID
        body: Optional JSON body with format: {"activation_keys": {product_id: "key", ...}}
    """
    business_id = get_business_id(current_user)
    # Get the order
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.business_id == business_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Extract activation_keys from body if provided
    activation_keys = None
    if body and "activation_keys" in body:
        activation_keys = body["activation_keys"]
    
    # Get ALL orders with the same yandex_order_id (one order record per item) for this business
    yandex_order_id = order.yandex_order_id
    all_orders = db.query(models.Order).filter(
        models.Order.yandex_order_id == yandex_order_id,
        models.Order.business_id == business_id
    ).all()
    
    order_service = OrderService(db)
    result = order_service.complete_order_with_all_items(all_orders, manual_activation_keys=activation_keys)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/{order_id}/mark-finished", response_model=dict)
def mark_order_finished(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark order as finished (after completing buyer interaction)
    
    This sets the status to FINISHED, which will not be overridden by Yandex API status updates.
    The UI will show "finished" even if Yandex API says DELIVERED.
    """
    business_id = get_business_id(current_user)
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.business_id == business_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != models.OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Only completed orders can be marked as finished")
    
    # Get ALL orders with the same yandex_order_id and update them all (for this business)
    yandex_order_id = order.yandex_order_id
    all_orders = db.query(models.Order).filter(
        models.Order.yandex_order_id == yandex_order_id,
        models.Order.business_id == business_id
    ).all()
    
    # Set status to FINISHED for all orders in this group
    # This status will not be overridden by Yandex API updates
    for o in all_orders:
        o.status = models.OrderStatus.FINISHED
    
    db.commit()
    db.refresh(order)
    
    # Convert order to dict for serialization
    order_dict = {
        "id": order.id,
        "yandex_order_id": order.yandex_order_id,
        "product_id": order.product_id,
        "customer_name": order.customer_name,
        "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
        "total_amount": float(order.total_amount) if order.total_amount else 0,
        "quantity": order.quantity,
        "activation_code_sent": order.activation_code_sent,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
    }
    
    return {"success": True, "message": "Order marked as finished", "order": order_dict}
