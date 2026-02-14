from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, has_permission, get_business_id

router = APIRouter()


def _get_date_range(
    period: Optional[str] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None
) -> tuple:
    """Get start and end date for period filter or custom date range"""
    # If custom date range is provided, use it
    if start_date_str and end_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            # Set end_date to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_date, end_date
        except Exception:
            # If parsing fails, fall back to period
            pass
    
    # Use period if no custom dates provided
    if not period or period == "all":
        return None, None
    
    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_date, now
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_date, now
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_date, now
    return None, None


@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    period: Optional[str] = Query(None, description="Period: today, week, month, or all"),
    start_date: Optional[str] = Query(None, alias="start_date", description="Start date (ISO format) for custom range"),
    end_date: Optional[str] = Query(None, alias="end_date", description="End date (ISO format) for custom range"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics with optional period filter or custom date range. Revenue/profit data requires dashboard_right permission."""
    business_id = get_business_id(current_user)
    total_products = db.query(models.Product).filter(models.Product.business_id == business_id).count()
    active_products = db.query(models.Product).filter(
        models.Product.business_id == business_id,
        models.Product.is_active == True
    ).count()
    
    # Get date range for period filter or custom dates
    start_date_dt, end_date_dt = _get_date_range(period, start_date, end_date)
    
    # Build order queries with period filter
    # Count unique orders by yandex_order_id (not individual order records)
    base_query = db.query(models.Order).filter(models.Order.business_id == business_id)
    if start_date_dt:
        base_query = base_query.filter(models.Order.created_at >= start_date_dt)
    if end_date_dt:
        base_query = base_query.filter(models.Order.created_at <= end_date_dt)
    
    # Count unique orders (by yandex_order_id)
    total_orders = base_query.with_entities(func.distinct(models.Order.yandex_order_id)).count()
    
    # Count orders by status (unique yandex_order_id)
    pending_query = base_query.filter(models.Order.status == models.OrderStatus.PENDING)
    processing_query = base_query.filter(models.Order.status == models.OrderStatus.PROCESSING)
    completed_query = base_query.filter(models.Order.status == models.OrderStatus.COMPLETED)
    cancelled_query = base_query.filter(models.Order.status == models.OrderStatus.CANCELLED)
    finished_query = base_query.filter(models.Order.status == models.OrderStatus.FINISHED)
    
    pending_orders = pending_query.with_entities(func.distinct(models.Order.yandex_order_id)).count()
    processing_orders = processing_query.with_entities(func.distinct(models.Order.yandex_order_id)).count()
    completed_orders = completed_query.with_entities(func.distinct(models.Order.yandex_order_id)).count()
    cancelled_orders = cancelled_query.with_entities(func.distinct(models.Order.yandex_order_id)).count()
    finished_orders = finished_query.with_entities(func.distinct(models.Order.yandex_order_id)).count()
    
    # Count successful orders (completed + finished)
    successful_orders = completed_orders + finished_orders
    
    # Check if user has permission to view analytics
    has_dashboard_right = current_user.is_admin or has_permission(current_user, "dashboard_right")
    
    # Calculate revenue and profit only if user has permission
    total_revenue = 0.0
    total_profit = 0.0
    total_cost = 0.0
    profit_margin = 0.0
    
    if has_dashboard_right:
        # Query for revenue/profit calculation (COMPLETED and FINISHED orders - both mean payment received)
        completed_or_finished_query = base_query.filter(
            (models.Order.status == models.OrderStatus.COMPLETED) |
            (models.Order.status == models.OrderStatus.FINISHED)
        )
        
        # Calculate revenue and profit from COMPLETED and FINISHED orders (both mean payment received)
        completed_or_finished_list = completed_or_finished_query.all()
        
        # Group by yandex_order_id to avoid double-counting multi-item orders
        orders_by_yandex_id = {}
        for order in completed_or_finished_list:
            yandex_id = order.yandex_order_id
            if yandex_id not in orders_by_yandex_id:
                orders_by_yandex_id[yandex_id] = []
            orders_by_yandex_id[yandex_id].append(order)
        
        # Calculate revenue and profit (sum all items per unique order)
        for yandex_id, order_group in orders_by_yandex_id.items():
            # Sum all items in this order
            order_total = sum(o.total_amount for o in order_group)
            total_revenue += order_total
            
            # Calculate profit for all items
            for order in order_group:
                try:
                    total_profit += order.profit
                except Exception as e:
                    print(f"Warning: Failed to calculate profit for order {order.id}: {str(e)}")
                    # Fallback: use order total as profit if product lookup fails
                    total_profit += order.total_amount
        
        total_cost = total_revenue - total_profit
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return schemas.DashboardStats(
        total_products=total_products,
        active_products=active_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        processing_orders=processing_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        finished_orders=finished_orders,
        successful_orders=successful_orders,
        total_revenue=total_revenue,
        total_profit=total_profit,
        total_cost=total_cost,
        profit_margin=profit_margin
    )


@router.get("/top-products", response_model=List[schemas.TopProduct])
def get_top_products(
    limit: int = 10,
    period: Optional[str] = Query(None, description="Period: today, week, month, or all"),
    start_date: Optional[str] = Query(None, alias="start_date", description="Start date (ISO format) for custom range"),
    end_date: Optional[str] = Query(None, alias="end_date", description="End date (ISO format) for custom range"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get top selling products with optional period filter or custom date range. Revenue/profit data requires dashboard_right permission."""
    start_date_dt, end_date_dt = _get_date_range(period, start_date, end_date)
    
    business_id = get_business_id(current_user)
    query = (
        db.query(
            models.Product.id,
            models.Product.name,
            func.count(func.distinct(models.Order.yandex_order_id)).label("total_sales"),  # Count unique orders, not order records
            func.sum(models.Order.total_amount).label("total_revenue"),
            func.sum(models.Order.total_amount - (models.Product.cost_price * models.Order.quantity)).label("total_profit")
        )
        .join(models.Order)
        .filter(
            models.Product.business_id == business_id,
            models.Order.business_id == business_id,
            (models.Order.status == models.OrderStatus.COMPLETED) |
            (models.Order.status == models.OrderStatus.FINISHED)
        )
    )
    
    if start_date_dt:
        query = query.filter(models.Order.created_at >= start_date_dt)
    if end_date_dt:
        query = query.filter(models.Order.created_at <= end_date_dt)
    
    top_products = (
        query
        .group_by(models.Product.id, models.Product.name)
        .order_by(desc("total_sales"))
        .limit(limit)
        .all()
    )
    
    # Check if user has permission to view analytics
    has_dashboard_right = current_user.is_admin or has_permission(current_user, "dashboard_right")
    
    return [
        schemas.TopProduct(
            product_id=product.id,
            product_name=product.name,
            total_sales=product.total_sales,
            total_revenue=float(product.total_revenue or 0) if has_dashboard_right else 0.0,
            total_profit=float(product.total_profit or 0) if has_dashboard_right else 0.0
        )
        for product in top_products
    ]


@router.get("/recent-orders", response_model=List[schemas.Order])
def get_recent_orders(
    limit: int = 10,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recent orders grouped by yandex_order_id (same logic as get_orders)"""
    from app.routers.orders import get_orders as get_orders_endpoint
    
    # Filter by business_id for data isolation
    business_id = get_business_id(current_user)
    
    # Use the same logic as get_orders endpoint to ensure consistency
    # Get more orders to account for grouping
    orders = (
        db.query(models.Order)
        .filter(models.Order.business_id == business_id)
        .order_by(desc(models.Order.created_at))
        .limit(limit * 10)  # Get more to account for grouping
        .all()
    )
    
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
        all_activation_sent = True
        
        # Get yandex_order_data to extract item IDs
        yandex_order_data = base_order.yandex_order_data or {}
        if isinstance(yandex_order_data, str):
            import json
            try:
                yandex_order_data = json.loads(yandex_order_data)
            except:
                yandex_order_data = {}
        
        # Extract items from yandex_order_data
        yandex_items = yandex_order_data.get("items", [])
        if not yandex_items and isinstance(yandex_order_data, dict) and "order" in yandex_order_data:
            yandex_items = yandex_order_data["order"].get("items", [])
        
        # Build items array from Yandex items (source of truth)
        processed_yandex_item_ids = set()
        
        # First, process items that have matching order records in database
        for o in order_group:
            product = db.query(models.Product).filter(
                models.Product.id == o.product_id,
                models.Product.business_id == business_id
            ).first()
            if product:
                # Find matching Yandex item
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
                
                # Use price from Yandex item if available
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
        
        # Second, process Yandex items that DON'T have matching order records
        for yandex_item in yandex_items:
            yandex_item_id = yandex_item.get("id")
            if yandex_item_id in processed_yandex_item_ids:
                continue
            
            offer_id = yandex_item.get("offerId") or yandex_item.get("shopSku")
            item_price = float(yandex_item.get("price") or yandex_item.get("buyerPrice") or 0)
            item_count = yandex_item.get("count", 1)
            item_total = item_price * item_count
            item_name = yandex_item.get("offerName") or offer_id or "Unknown Product"
            
            # Try to find product in database - filter by business_id
            product = db.query(models.Product).filter(
                models.Product.business_id == business_id,
                (
                    (models.Product.yandex_market_id == offer_id) |
                    (models.Product.yandex_market_id == yandex_item.get("shopSku")) |
                    (models.Product.yandex_market_sku == offer_id) |
                    (models.Product.yandex_market_sku == yandex_item.get("shopSku"))
                )
            ).first()
            
            if product:
                order_items.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item_count,
                    "item_price": item_price,
                    "item_total": item_total,
                    "yandex_item_id": yandex_item_id,
                    "yandex_offer_id": offer_id,
                    "activation_code_sent": False,
                    "activation_key_id": None,
                    "email_template_id": product.email_template_id,
                    "documentation_id": product.documentation_id,
                })
            else:
                order_items.append({
                    "product_id": None,
                    "product_name": item_name,
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
        
        # Convert order_items to OrderItem schema objects
        order_item_objects = [
            schemas.OrderItem(**item) for item in order_items
        ]
        
        # Build order dict with items
        order_dict = {
            **base_order.__dict__,
            "product_name": order_items[0]["product_name"] if order_items else None,
            "total_amount": total_amount,
            "items": order_item_objects,
            "items_count": len(order_items),
            "activation_code_sent": all_activation_sent,
        }
        
        # Auto-complete DELIVERED orders: If Yandex status is DELIVERED and we've sent activation codes, mark as completed
        # Auto-complete DELIVERED orders: If Yandex status is DELIVERED and we've sent activation codes, mark as completed
        # But only if status is not already FINISHED (manual override takes precedence)
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
        
        # IMPORTANT: Always use the actual status from database - FINISHED status takes precedence over Yandex API
        # Refresh base_order one more time to ensure we have the absolute latest status from database
        db.refresh(base_order)
        order_dict["status"] = base_order.status  # CRITICAL: Use actual database status (FINISHED takes precedence over everything)
        
        # Convert to Order schema
        order_schema = schemas.Order(**order_dict)
        result.append(order_schema)
        
        # Limit results
        if len(result) >= limit:
            break
    
    return result


@router.get("/data", response_model=schemas.DashboardData)
def get_dashboard_data(
    period: Optional[str] = Query(None, description="Period: today, week, month, or all"),
    start_date: Optional[str] = Query(None, alias="start_date", description="Start date (ISO format) for custom range"),
    end_date: Optional[str] = Query(None, alias="end_date", description="End date (ISO format) for custom range"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete dashboard data with optional period filter or custom date range"""
    try:
        stats = get_dashboard_stats(period=period, start_date=start_date, end_date=end_date, current_user=current_user, db=db)
        top_products = get_top_products(limit=10, period=period, start_date=start_date, end_date=end_date, current_user=current_user, db=db)
        recent_orders = get_recent_orders(limit=10, current_user=current_user, db=db)
        
        return schemas.DashboardData(
            stats=stats,
            top_products=top_products,
            recent_orders=recent_orders
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error in get_dashboard_data: {str(e)}")
        print(traceback.format_exc())
        raise
