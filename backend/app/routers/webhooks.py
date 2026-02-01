from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services.order_service import OrderService
from app.services.telegram_bot import telegram_bot
from typing import Dict, Any

router = APIRouter()


@router.post("/yandex-market/orders")
async def yandex_market_webhook(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Yandex Market order notifications
    This endpoint automatically receives order updates from Yandex Market in real-time
    Configure this URL in Yandex Market Partner Dashboard → API and modules → API notifications
    """
    try:
        event_type = payload.get("event")
        order_data = payload.get("order", {})
        
        # Handle various Yandex Market webhook event types
        # If order_data is empty, try getting order directly from payload
        if not order_data and "order" in payload:
            order_data = payload.get("order", {})
        
        if event_type in ["ORDER_CREATED", "ORDER_UPDATED", "ORDER_STATUS_CHANGED"] or "order" in payload:
            if not order_data or not order_data.get("id"):
                return {"success": False, "message": "Invalid order data in webhook payload"}
            
            yandex_order_id = str(order_data.get("id"))
            
            # Check if order already exists
            existing_order = db.query(models.Order).filter(
                models.Order.yandex_order_id == yandex_order_id
            ).first()
            
            if existing_order:
                # Update existing order
                old_status = existing_order.status
                existing_order.status = _map_yandex_status(order_data.get("status"))
                existing_order.total_amount = float(order_data.get("totalAmount", 0))
                db.commit()
                
                # Send Telegram notification if status changed
                if old_status != existing_order.status:
                    if existing_order.status == models.OrderStatus.COMPLETED:
                        telegram_bot.send_order_notification_sync(existing_order, "completed")
                    else:
                        telegram_bot.send_order_notification_sync(existing_order, "status_changed")
                
                return {"success": True, "message": "Order updated"}
            else:
                # Create new order
                # Find product by SKU or Yandex Market ID
                product = db.query(models.Product).filter(
                    (models.Product.yandex_market_sku == order_data.get("sku")) |
                    (models.Product.yandex_market_id == str(order_data.get("productId", "")))
                ).first()
                
                if not product:
                    return {"success": False, "message": "Product not found for order"}
                
                # Note: Yandex Market API typically does NOT provide customer email/phone for privacy
                # Email will only be available if customer provides it in chat (you can update it manually)
                new_order = models.Order(
                    yandex_order_id=yandex_order_id,
                    product_id=product.id,
                    customer_name=order_data.get("customer", {}).get("name"),  # May be None
                    customer_email=order_data.get("customer", {}).get("email"),  # Usually None - only if provided in chat
                    customer_phone=order_data.get("customer", {}).get("phone"),  # Usually None
                    quantity=order_data.get("quantity", 1),
                    total_amount=float(order_data.get("totalAmount", 0)),
                    status=_map_yandex_status(order_data.get("status"))
                )
                db.add(new_order)
                db.commit()
                db.refresh(new_order)
                
                # Auto-fulfill digital products
                if product.product_type == models.ProductType.DIGITAL:
                    order_service = OrderService(db)
                    order_service.auto_fulfill_order(new_order)
                
                # Send Telegram notification for new order
                telegram_bot.send_order_notification_sync(new_order, "created")
                
                return {"success": True, "message": "Order created and processed"}
        
        return {"success": True, "message": "Webhook received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


def _map_yandex_status(yandex_status: str) -> models.OrderStatus:
    """Map Yandex Market order status to our OrderStatus enum"""
    status_mapping = {
        "PROCESSING": models.OrderStatus.PROCESSING,
        "DELIVERY": models.OrderStatus.PROCESSING,
        "DELIVERED": models.OrderStatus.COMPLETED,
        "CANCELLED": models.OrderStatus.CANCELLED,
        "PENDING": models.OrderStatus.PENDING,
    }
    return status_mapping.get(yandex_status.upper(), models.OrderStatus.PENDING)
