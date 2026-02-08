from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, or_ as sql_or, func
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Client])
def get_clients(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    start_date: Optional[str] = Query(None, description="Filter by created_at start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by created_at end date (ISO format)"),
    db: Session = Depends(get_db)
):
    """Get all clients, optionally filtered by product purchase, search, or date range"""
    from datetime import datetime
    
    query = db.query(models.Client)
    
    # Filter by product if provided
    if product_id is not None:
        query = query.join(models.Client.purchased_products).filter(
            models.Product.id == product_id
        )
    
    # Search by name or email
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            sql_or(
                func.lower(models.Client.name).like(search_term),
                func.lower(models.Client.email).like(search_term)
            )
        )
    
    # Filter by created_at date range
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(models.Client.created_at >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(models.Client.created_at <= end_dt)
        except:
            pass
    
    clients = query.all()
    
    # Add purchased_product_ids to each client
    for client in clients:
        client.purchased_product_ids = [p.id for p in client.purchased_products]
    return clients

@router.post("/", response_model=schemas.Client)
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    """Create a new client or update existing one if email exists"""
    # Check if email already exists
    existing = db.query(models.Client).filter(models.Client.email == client.email).first()
    
    purchased_product_ids = client.purchased_product_ids or []
    
    if existing:
        # Update existing client - merge new products with existing
        if purchased_product_ids:
            # Get current product IDs
            current_product_ids = {p.id for p in existing.purchased_products}
            new_product_ids = set(purchased_product_ids) - current_product_ids
            
            if new_product_ids:
                # Add new products to existing client
                new_products = db.query(models.Product).filter(
                    models.Product.id.in_(new_product_ids)
                ).all()
                
                # Add new products with quantity 1
                for product in new_products:
                    existing.purchased_products.append(product)
                
                # Update client's updated_at timestamp
                existing.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(existing)
        
        existing.purchased_product_ids = [p.id for p in existing.purchased_products]
        return existing
    
    # Create new client
    client_data = client.dict(exclude={'purchased_product_ids'})
    db_client = models.Client(**client_data)
    
    # Add purchased products
    if purchased_product_ids:
        products = db.query(models.Product).filter(models.Product.id.in_(purchased_product_ids)).all()
        db_client.purchased_products = products
    
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    db_client.purchased_product_ids = [p.id for p in db_client.purchased_products]
    
    return db_client

@router.get("/{client_id}", response_model=schemas.Client)
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a specific client"""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.purchased_product_ids = [p.id for p in client.purchased_products]
    return client

@router.put("/{client_id}", response_model=schemas.Client)
def update_client(
    client_id: int,
    client_update: schemas.ClientUpdate,
    db: Session = Depends(get_db)
):
    """Update a client"""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check email uniqueness if being updated
    if client_update.email and client_update.email != client.email:
        existing = db.query(models.Client).filter(models.Client.email == client_update.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    update_data = client_update.dict(exclude_unset=True, exclude={'purchased_product_ids'})
    for field, value in update_data.items():
        setattr(client, field, value)
    
    # Update purchased products if provided
    if client_update.purchased_product_ids is not None:
        products = db.query(models.Product).filter(
            models.Product.id.in_(client_update.purchased_product_ids)
        ).all()
        client.purchased_products = products
    
    db.commit()
    db.refresh(client)
    client.purchased_product_ids = [p.id for p in client.purchased_products]
    return client

@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Delete a client"""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    return {"message": "Client deleted successfully"}

@router.post("/{client_id}/increment-purchase/{product_id}")
def increment_purchase(
    client_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    """Increment the purchase quantity for a specific product"""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if client has this product
    if product not in client.purchased_products:
        raise HTTPException(status_code=400, detail="Client hasn't purchased this product")
    
    # Increment quantity and update last_purchase_date using raw SQL
    db.execute(text("""
        UPDATE client_products 
        SET quantity = quantity + 1,
            last_purchase_date = CURRENT_TIMESTAMP
        WHERE client_id = :client_id AND product_id = :product_id
    """), {"client_id": client_id, "product_id": product_id})
    
    # Update client's updated_at
    client.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Get updated quantity
    result = db.execute(text("""
        SELECT quantity FROM client_products 
        WHERE client_id = :client_id AND product_id = :product_id
    """), {"client_id": client_id, "product_id": product_id})
    quantity = result.scalar()
    
    return {
        "message": "Purchase incremented successfully",
        "client_id": client_id,
        "product_id": product_id,
        "new_quantity": quantity
    }
