from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app import models
from app.services.yandex_api import YandexMarketAPI


class OrderService:
    """Service for handling order fulfillment"""
    
    def __init__(self, db: Session):
        self.db = db
        self.yandex_api = YandexMarketAPI()
    
    def auto_fulfill_order(self, order: models.Order) -> dict:
        """Automatically fulfill order for digital products"""
        # Get product using query
        product = self.db.query(models.Product).filter(models.Product.id == order.product_id).first()
        if not product:
            return {"success": False, "message": "Product not found"}
        
        if product.product_type != models.ProductType.DIGITAL:
            return {"success": False, "message": "Only digital products can be auto-fulfilled"}
        
        # Get an unused activation key
        activation_key = self.db.query(models.ActivationKey).filter(
            models.ActivationKey.product_id == order.product_id,
            models.ActivationKey.is_used == False
        ).first()
        
        if not activation_key:
            # Generate a new key if none available
            import secrets
            key = f"{product.yandex_market_sku or product.id}-{secrets.token_urlsafe(16)}"
            activation_key = models.ActivationKey(
                product_id=order.product_id,
                key=key
            )
            self.db.add(activation_key)
            self.db.flush()
        
        # Assign key to order
        order.activation_key_id = activation_key.id
        activation_key.is_used = True
        activation_key.used_at = datetime.utcnow()
        
        # Update order status
        order.status = models.OrderStatus.PROCESSING
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Order fulfilled successfully",
            "activation_key": activation_key.key
        }
    
    def fulfill_order(self, order: models.Order) -> dict:
        """Manually fulfill an order"""
        result = self.auto_fulfill_order(order)
        
        if result["success"]:
            # Accept order on Yandex Market
            try:
                self.yandex_api.accept_order(order.yandex_order_id)
            except Exception as e:
                # Log error but don't fail
                print(f"Failed to accept order on Yandex Market: {str(e)}")
        
        return result
    
    def complete_order_with_code(self, order: models.Order, activation_code: str) -> dict:
        """Complete order by sending activation code to Yandex Market"""
        # Get activation key using query
        activation_key = self.db.query(models.ActivationKey).filter(
            models.ActivationKey.id == order.activation_key_id
        ).first()
        
        if not activation_key:
            raise ValueError("Order has no activation key assigned")
        
        try:
            # Send activation code to Yandex Market
            self.yandex_api.complete_order(order.yandex_order_id, activation_code)
            
            # Update order status
            order.status = models.OrderStatus.COMPLETED
            order.completed_at = datetime.utcnow()
            self.db.commit()
            
            return {"success": True, "message": "Order completed successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to complete order: {str(e)}"}
