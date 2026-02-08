from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services.order_service import OrderService
from typing import Dict, Any

router = APIRouter()


def _map_yandex_status(yandex_status: str) -> models.OrderStatus:
    """Map Yandex Market order status to our OrderStatus enum"""
    if not yandex_status:
        return models.OrderStatus.PENDING
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
    return status_mapping.get(yandex_status.upper(), models.OrderStatus.PENDING)


@router.post("/yandex-market/orders")
async def yandex_market_webhook(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Yandex Market order notifications.
    
    Yandex Market sends order data with 'items' array containing:
    - id: item ID (needed for deliverDigitalGoods)
    - offerId: matches Product.yandex_market_id
    - count: quantity
    - price: unit price
    
    Customer info uses 'buyer' field (not 'customer').
    """
    try:
        event_type = payload.get("event")
        order_data = payload.get("order", {})
        
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
                # Update ALL order records with the same yandex_order_id (one record per item)
                # Yandex API is source of truth - ensure we have Order records for ALL items
                all_orders = db.query(models.Order).filter(
                    models.Order.yandex_order_id == yandex_order_id
                ).all()
                
                # Get all product IDs that already have order records
                existing_product_ids = {o.product_id for o in all_orders}
                
                old_status = existing_order.status
                new_yandex_status = order_data.get("status", "")
                mapped_status = _map_yandex_status(new_yandex_status)
                
                # Update all existing order records with the same yandex_order_id
                # CRITICAL: Never override FINISHED status except with CANCELLED
                for order_record in all_orders:
                    # Always update yandex_order_data and yandex_status
                    order_record.yandex_order_data = order_data
                    order_record.yandex_status = new_yandex_status
                    
                    # CRITICAL: Never override FINISHED status except with CANCELLED
                    # FINISHED is a manual override that takes precedence over all Yandex API statuses
                    if order_record.status == models.OrderStatus.FINISHED:
                        # Only allow CANCELLED to override FINISHED
                        if mapped_status == models.OrderStatus.CANCELLED:
                            order_record.status = mapped_status
                            print(f"  ⚠️  Webhook: Order {yandex_order_id} FINISHED status overridden by CANCELLED from Yandex")
                        else:
                            # Keep FINISHED status, don't update from Yandex API
                            print(f"  ℹ️  Webhook: Order {yandex_order_id} keeping FINISHED status (Yandex status: {new_yandex_status} ignored)")
                            continue  # Skip status update for this order
                    else:
                        # Not FINISHED, update status normally
                        order_record.status = mapped_status
                        
                        # Update total from order-level fields
                        total = order_data.get("total") or order_data.get("itemsTotal") or order_data.get("buyerTotal")
                        if total:
                            # For multi-item orders, calculate item total from items array
                            items = order_data.get("items", [])
                            if items:
                                # Find matching item for this order record
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
                                            order_record.quantity = item_count
                                            break
                            else:
                                # Fallback to order total divided by number of items
                                order_record.total_amount = float(total) / len(all_orders) if all_orders else float(total)
                        else:
                            order_record.total_amount = float(total) if total else order_record.total_amount
                
                # Check for new items in Yandex order that don't have order records yet
                # Yandex API is source of truth - create Order records for ALL items
                items = order_data.get("items", [])
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
                        buyer = order_data.get("buyer", {})
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
                            yandex_order_data=order_data,
                        )
                        db.add(new_order)
                        db.flush()
                        
                        # Auto-fulfill digital products
                        if product.product_type == models.ProductType.DIGITAL:
                            order_service = OrderService(db)
                            order_service.auto_fulfill_order(new_order)
                        
                        existing_product_ids.add(product.id)  # Mark as processed
                        print(f"  ✅ Webhook: Created missing order record for product {product.id} ({product.name}) in order {yandex_order_id}")
                
                db.commit()
                
                return {"success": True, "message": "Order updated"}
            else:
                # Create new order - use shared parser from main.py
                # Yandex API is source of truth - create ONE Order record per item
                from app.main import _parse_yandex_order
                
                parsed_orders = _parse_yandex_order(order_data, db)
                
                if not parsed_orders:
                    items = order_data.get("items", [])
                    print(f"⚠️  Webhook: Order {yandex_order_id} has {len(items)} items but no products matched in database")
                    print(f"      Items: {[item.get('offerId') or item.get('shopSku') for item in items]}")
                    return {"success": False, "message": f"Product not found for order items. Order has {len(items)} items."}
                
                created_count = 0
                for new_order, product in parsed_orders:
                    # Check if this order record already exists (composite unique: yandex_order_id + product_id)
                    existing = db.query(models.Order).filter(
                        models.Order.yandex_order_id == new_order.yandex_order_id,
                        models.Order.product_id == new_order.product_id
                    ).first()
                    
                    if existing:
                        # Update existing order record
                        # CRITICAL: Never override FINISHED status except with CANCELLED
                        existing.yandex_status = new_order.yandex_status
                        existing.yandex_order_data = new_order.yandex_order_data
                        existing.quantity = new_order.quantity
                        existing.total_amount = new_order.total_amount
                        existing.customer_name = new_order.customer_name
                        
                        # Only update status if it's not already FINISHED (or if new status is CANCELLED)
                        if existing.status == models.OrderStatus.FINISHED:
                            # Only allow CANCELLED to override FINISHED
                            if new_order.status == models.OrderStatus.CANCELLED:
                                existing.status = new_order.status
                                print(f"  ⚠️  Webhook: Order {yandex_order_id} FINISHED status overridden by CANCELLED")
                            else:
                                print(f"  ℹ️  Webhook: Order {yandex_order_id} keeping FINISHED status (new status: {new_order.status} ignored)")
                        else:
                            # Not FINISHED, update status normally
                            existing.status = new_order.status
                        
                        print(f"  ✅ Webhook: Updated existing order record for product {product.id} in order {yandex_order_id}")
                    else:
                        # Create new order record
                        db.add(new_order)
                        db.flush()
                        
                        # Auto-fulfill digital products
                        if product.product_type == models.ProductType.DIGITAL:
                            order_service = OrderService(db)
                            order_service.auto_fulfill_order(new_order)
                        
                        created_count += 1
                        print(f"  ✅ Webhook: Created order record for product {product.id} ({product.name}) in order {yandex_order_id}")
                
                db.commit()
                
                return {"success": True, "message": f"{created_count} order(s) created and processed"}
        
        return {"success": True, "message": "Webhook received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
