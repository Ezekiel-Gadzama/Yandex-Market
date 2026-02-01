from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas

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
    db: Session = Depends(get_db)
):
    """Get dashboard statistics with optional period filter or custom date range"""
    total_products = db.query(models.Product).count()
    active_products = db.query(models.Product).filter(models.Product.is_active == True).count()
    
    # Get date range for period filter or custom dates
    start_date_dt, end_date_dt = _get_date_range(period, start_date, end_date)
    
    # Build order queries with period filter
    orders_query = db.query(models.Order)
    completed_orders_query = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.COMPLETED
    )
    
    if start_date_dt:
        orders_query = orders_query.filter(models.Order.created_at >= start_date_dt)
        completed_orders_query = completed_orders_query.filter(models.Order.created_at >= start_date_dt)
    if end_date_dt:
        orders_query = orders_query.filter(models.Order.created_at <= end_date_dt)
        completed_orders_query = completed_orders_query.filter(models.Order.created_at <= end_date_dt)
    
    total_orders = orders_query.count()
    pending_orders = orders_query.filter(
        models.Order.status == models.OrderStatus.PENDING
    ).count()
    completed_orders = completed_orders_query.count()
    
    # Calculate revenue and profit
    completed_orders_list = completed_orders_query.all()
    
    total_revenue = sum(order.total_amount for order in completed_orders_list)
    total_profit = sum(order.get_profit(db) for order in completed_orders_list)
    total_cost = total_revenue - total_profit
    
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return schemas.DashboardStats(
        total_products=total_products,
        active_products=active_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
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
    db: Session = Depends(get_db)
):
    """Get top selling products with optional period filter or custom date range"""
    start_date_dt, end_date_dt = _get_date_range(period, start_date, end_date)
    
    query = (
        db.query(
            models.Product.id,
            models.Product.name,
            func.count(models.Order.id).label("total_sales"),
            func.sum(models.Order.total_amount).label("total_revenue"),
            func.sum(models.Order.total_amount - (models.Product.cost_price * models.Order.quantity)).label("total_profit")
        )
        .join(models.Order)
        .filter(models.Order.status == models.OrderStatus.COMPLETED)
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
    
    return [
        schemas.TopProduct(
            product_id=product.id,
            product_name=product.name,
            total_sales=product.total_sales,
            total_revenue=float(product.total_revenue or 0),
            total_profit=float(product.total_profit or 0)
        )
        for product in top_products
    ]


@router.get("/recent-orders", response_model=List[schemas.Order])
def get_recent_orders(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent orders"""
    orders = (
        db.query(models.Order)
        .order_by(desc(models.Order.created_at))
        .limit(limit)
        .all()
    )
    return orders


@router.get("/data", response_model=schemas.DashboardData)
def get_dashboard_data(
    period: Optional[str] = Query(None, description="Period: today, week, month, or all"),
    start_date: Optional[str] = Query(None, alias="start_date", description="Start date (ISO format) for custom range"),
    end_date: Optional[str] = Query(None, alias="end_date", description="End date (ISO format) for custom range"),
    db: Session = Depends(get_db)
):
    """Get complete dashboard data with optional period filter or custom date range"""
    stats = get_dashboard_stats(period=period, start_date=start_date, end_date=end_date, db=db)
    top_products = get_top_products(limit=10, period=period, start_date=start_date, end_date=end_date, db=db)
    recent_orders = get_recent_orders(limit=10, db=db)
    
    return schemas.DashboardData(
        stats=stats,
        top_products=top_products,
        recent_orders=recent_orders
    )
