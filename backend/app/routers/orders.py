from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.services.order_service import OrderService
from app.services.email_service import EmailService

router = APIRouter()


@router.get("/", response_model=List[schemas.Order])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get all orders with optional filters"""
    query = db.query(models.Order)
    
    if status:
        query = query.filter(models.Order.status == status)
    
    orders = query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a single order by ID"""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Create a new order (typically from Yandex Market webhook)"""
    # Check if order already exists
    existing = db.query(models.Order).filter(
        models.Order.yandex_order_id == order.yandex_order_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Order already exists")
    
    db_order = models.Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Auto-process digital products
    product = db.query(models.Product).filter(models.Product.id == db_order.product_id).first()
    if product and product.product_type == models.ProductType.DIGITAL:
        order_service = OrderService(db)
        order_service.auto_fulfill_order(db_order)
    
    return db_order


@router.put("/{order_id}", response_model=schemas.Order)
def update_order(
    order_id: int,
    order_update: schemas.OrderUpdate,
    db: Session = Depends(get_db)
):
    """Update an order"""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    db.commit()
    db.refresh(db_order)
    return db_order


@router.post("/{order_id}/fulfill", response_model=dict)
def fulfill_order(order_id: int, db: Session = Depends(get_db)):
    """Manually fulfill an order (assign activation key and send email)"""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.product_type != models.ProductType.DIGITAL:
        raise HTTPException(status_code=400, detail="Only digital products can be fulfilled with activation keys")
    
    order_service = OrderService(db)
    result = order_service.fulfill_order(order)
    
    return result


@router.post("/{order_id}/send-activation-email", response_model=dict)
def send_activation_email(order_id: int, db: Session = Depends(get_db)):
    """Send activation email to customer
    
    IMPORTANT: Yandex Market automatically sends activation emails when you complete the order via API.
    This endpoint is ONLY useful if:
    - Customer provided their email in chat and you want to send additional/custom messages
    - You want to send follow-up emails outside of Yandex's system
    
    Note: Yandex Market API typically does NOT provide customer email addresses.
    You'll need to manually add the email if customer provides it in chat.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    activation_key = db.query(models.ActivationKey).filter(
        models.ActivationKey.id == order.activation_key_id
    ).first()
    
    if not activation_key:
        raise HTTPException(status_code=400, detail="Order has no activation key assigned")
    
    email_service = EmailService()
    result = email_service.send_activation_email(order, db)
    
    return result


@router.post("/{order_id}/complete", response_model=schemas.Order)
def complete_order(order_id: int, db: Session = Depends(get_db)):
    """Mark order as completed"""
    from datetime import datetime
    
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = models.OrderStatus.COMPLETED
    order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    
    return order
