from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import text, or_ as sql_or, func
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, has_permission, get_business_id

router = APIRouter()

def _add_product_quantities(client, db):
    """Helper function to add product_quantities to a client object"""
    product_quantities = {}
    for product in client.purchased_products:
        result = db.execute(text("""
            SELECT quantity FROM client_products 
            WHERE client_id = :client_id AND product_id = :product_id
        """), {"client_id": client.id, "product_id": product.id})
        row = result.first()
        if row:
            product_quantities[product.id] = row[0] or 1
        else:
            product_quantities[product.id] = 1
    client.product_quantities = product_quantities
    return client

@router.get("/", response_model=List[schemas.Client])
def get_clients(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    start_date: Optional[str] = Query(None, description="Filter by created_at start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by created_at end date (ISO format)"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all clients, optionally filtered by product purchase, search, or date range. Only returns clients for the current user's business."""
    from datetime import datetime
    
    business_id = get_business_id(current_user)
    query = db.query(models.Client).filter(models.Client.business_id == business_id)
    
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
    
    # Add purchased_product_ids, product_quantities, and order_ids to each client
    for client in clients:
        client.purchased_product_ids = [p.id for p in client.purchased_products]
        if not client.order_ids:
            client.order_ids = []
        _add_product_quantities(client, db)
    return clients

@router.post("/", response_model=schemas.Client)
def create_client(
    client: schemas.ClientCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new client or update existing one if email exists. Requires client_right permission."""
    # Check permission (only for creating from clients page, not orders page)
    if not current_user.is_admin and not has_permission(current_user, "client_right"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: client_right"
        )
    import secrets
    
    business_id = get_business_id(current_user)
    # Check if email already exists for this business
    existing = db.query(models.Client).filter(
        models.Client.email == client.email,
        models.Client.business_id == business_id
    ).first()
    
    purchased_product_ids = client.purchased_product_ids or []
    
    # Generate unique buyer_id if creating new client (for manual creation)
    buyer_id = client.buyer_id  # Use provided buyer_id if available
    if not buyer_id and not existing:
        # Generate a unique buyer_id (UUID-like format similar to Yandex)
        buyer_id = secrets.token_hex(16)  # 32 character hex string
        # Ensure uniqueness
        while db.query(models.Client).filter(models.Client.buyer_id == buyer_id).first():
            buyer_id = secrets.token_hex(16)
    
    if existing:
        # Update existing client - merge new products with existing
        import json
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
                
                db.flush()
                
                # Set initial quantity and purchase history with current date for newly added products only
                current_date_str = datetime.utcnow().isoformat()
                for product in new_products:
                    purchase_dates_history = [current_date_str]
                    
                    db.execute(text("""
                        UPDATE client_products 
                        SET quantity = 1,
                            first_purchase_date = CURRENT_TIMESTAMP,
                            last_purchase_date = CURRENT_TIMESTAMP,
                            purchase_dates_history = CAST(:history AS jsonb)
                        WHERE client_id = :client_id AND product_id = :product_id
                    """), {
                        "client_id": existing.id,
                        "product_id": product.id,
                        "history": json.dumps(purchase_dates_history)
                    })
                
                # Update client's updated_at timestamp
                existing.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(existing)
        
        existing.purchased_product_ids = [p.id for p in existing.purchased_products]
        if not existing.order_ids:
            existing.order_ids = []
        _add_product_quantities(existing, db)
        return existing
    
    # Create new client
    import json
    client_data = client.dict(exclude={'purchased_product_ids'})
    db_client = models.Client(**client_data, buyer_id=buyer_id, business_id=business_id)
    
    # Add purchased products
    if purchased_product_ids:
        products = db.query(models.Product).filter(models.Product.id.in_(purchased_product_ids)).all()
        db_client.purchased_products = products
        db.add(db_client)
        db.flush()
        
        # Set initial quantity and purchase history with current date for all selected products
        current_date_str = datetime.utcnow().isoformat()
        for product in products:
            purchase_dates_history = [current_date_str]
            
            db.execute(text("""
                UPDATE client_products 
                SET quantity = 1,
                    first_purchase_date = CURRENT_TIMESTAMP,
                    last_purchase_date = CURRENT_TIMESTAMP,
                    purchase_dates_history = CAST(:history AS jsonb)
                WHERE client_id = :client_id AND product_id = :product_id
            """), {
                "client_id": db_client.id,
                "product_id": product.id,
                "history": json.dumps(purchase_dates_history)
            })
    else:
        db.add(db_client)
    
    db.commit()
    db.refresh(db_client)
    db_client.purchased_product_ids = [p.id for p in db_client.purchased_products]
    if not db_client.order_ids:
        db_client.order_ids = []
    _add_product_quantities(db_client, db)
    return db_client

@router.get("/{client_id}", response_model=schemas.Client)
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a specific client"""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.purchased_product_ids = [p.id for p in client.purchased_products]
    _add_product_quantities(client, db)
    return client

@router.put("/{client_id}", response_model=schemas.Client)
def update_client(
    client_id: int,
    client_update: schemas.ClientUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a client. Requires client_right permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "client_right"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: client_right"
        )
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
        import json
        
        # Get current product IDs
        current_product_ids = {p.id for p in client.purchased_products}
        new_product_ids = set(client_update.purchased_product_ids)
        
        # Find products to add (new ones)
        products_to_add = new_product_ids - current_product_ids
        # Find products to remove (ones not in new list)
        products_to_remove = current_product_ids - new_product_ids
        
        # Remove products that are no longer in the list
        if products_to_remove:
            products_to_remove_list = db.query(models.Product).filter(
                models.Product.id.in_(products_to_remove)
            ).all()
            for product in products_to_remove_list:
                if product in client.purchased_products:
                    client.purchased_products.remove(product)
        
        # Add new products (use current date for newly added products)
        if products_to_add:
            new_products = db.query(models.Product).filter(
                models.Product.id.in_(products_to_add)
            ).all()
            
            for product in new_products:
                client.purchased_products.append(product)
            
            db.flush()
            
            # Set initial quantity and purchase history with current date for newly added products only
            current_date_str = datetime.utcnow().isoformat()
            for product in new_products:
                purchase_dates_history = [current_date_str]
                
                db.execute(text("""
                    UPDATE client_products 
                    SET quantity = 1,
                        first_purchase_date = CURRENT_TIMESTAMP,
                        last_purchase_date = CURRENT_TIMESTAMP,
                        purchase_dates_history = CAST(:history AS jsonb)
                    WHERE client_id = :client_id AND product_id = :product_id
                """), {
                    "client_id": client.id,
                    "product_id": product.id,
                    "history": json.dumps(purchase_dates_history)
                })
        
        # Note: Existing products keep their original purchase dates (not updated)
    
    db.commit()
    db.refresh(client)
    client.purchased_product_ids = [p.id for p in client.purchased_products]
    _add_product_quantities(client, db)
    return client

@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a client. Requires client_right permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "client_right"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: client_right"
        )
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
    """Increment the purchase quantity for a specific product and update purchase history"""
    import json
    
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if client has this product
    if product not in client.purchased_products:
        raise HTTPException(status_code=400, detail="Client hasn't purchased this product")
    
    # Get current purchase history
    result = db.execute(text("""
        SELECT purchase_dates_history, last_purchase_date FROM client_products 
        WHERE client_id = :client_id AND product_id = :product_id
    """), {"client_id": client_id, "product_id": product_id})
    row = result.first()
    
    purchase_dates_history = row[0] if row and row[0] else []
    if isinstance(purchase_dates_history, str):
        purchase_dates_history = json.loads(purchase_dates_history)
    if not isinstance(purchase_dates_history, list):
        purchase_dates_history = []
    
    current_date = datetime.utcnow().isoformat()
    purchase_dates_history.append(current_date)
    
    # Increment quantity and update last_purchase_date and purchase_dates_history
    db.execute(text("""
        UPDATE client_products 
        SET quantity = quantity + 1,
            last_purchase_date = CURRENT_TIMESTAMP,
            purchase_dates_history = CAST(:history AS jsonb)
        WHERE client_id = :client_id AND product_id = :product_id
    """), {
        "client_id": client_id, 
        "product_id": product_id,
        "history": json.dumps(purchase_dates_history)
    })
    
    # Update client's updated_at
    client.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Get updated quantity and last purchase date
    result = db.execute(text("""
        SELECT quantity, last_purchase_date FROM client_products 
        WHERE client_id = :client_id AND product_id = :product_id
    """), {"client_id": client_id, "product_id": product_id})
    row = result.first()
    quantity = row[0] if row else 0
    last_purchase_date = row[1] if row else None
    
    return {
        "message": "Purchase incremented successfully",
        "client_id": client_id,
        "product_id": product_id,
        "new_quantity": quantity,
        "last_purchase_date": last_purchase_date.isoformat() if last_purchase_date else None
    }

@router.post("/{client_id}/decrement-purchase/{product_id}")
def decrement_purchase(
    client_id: int,
    product_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Decrement the purchase quantity for a specific product and revert to previous purchase date. Requires client_right permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "client_right"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: client_right"
        )
    import json
    
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if client has this product
    if product not in client.purchased_products:
        raise HTTPException(status_code=400, detail="Client hasn't purchased this product")
    
    # Get current purchase history and check if decrement is allowed (within 7 days)
    result = db.execute(text("""
        SELECT quantity, purchase_dates_history, last_purchase_date FROM client_products 
        WHERE client_id = :client_id AND product_id = :product_id
    """), {"client_id": client_id, "product_id": product_id})
    row = result.first()
    
    if not row or row[0] <= 0:
        raise HTTPException(status_code=400, detail="Cannot decrement: quantity is already 0")
    
    quantity = row[0]
    purchase_dates_history = row[1] if row and row[1] else []
    last_purchase_date = row[2] if row and row[2] else None
    
    if isinstance(purchase_dates_history, str):
        purchase_dates_history = json.loads(purchase_dates_history)
    if not isinstance(purchase_dates_history, list):
        purchase_dates_history = []
    
    # Check if last purchase was more than 7 days ago
    if last_purchase_date:
        days_since_purchase = (datetime.utcnow() - last_purchase_date.replace(tzinfo=None)).days
        if days_since_purchase > 7:
            raise HTTPException(status_code=400, detail="Cannot decrement: last purchase was more than 7 days ago")
    
    # Remove the last purchase date from history
    if purchase_dates_history:
        purchase_dates_history.pop()
    
    # Get the previous last purchase date
    previous_last_date = None
    if purchase_dates_history:
        try:
            previous_last_date = datetime.fromisoformat(purchase_dates_history[-1])
        except:
            pass
    
    # If quantity becomes 0, remove the product from client
    if quantity <= 1:
        # Remove product from client
        db.execute(text("""
            DELETE FROM client_products 
            WHERE client_id = :client_id AND product_id = :product_id
        """), {"client_id": client_id, "product_id": product_id})
        db.commit()
        return {
            "message": "Purchase decremented and product removed (quantity reached 0)",
            "client_id": client_id,
            "product_id": product_id,
            "new_quantity": 0,
            "previous_last_purchase_date": previous_last_date.isoformat() if previous_last_date else None
        }
    else:
        # Decrement quantity and update last_purchase_date to previous date
        update_sql = """
            UPDATE client_products 
            SET quantity = quantity - 1,
                purchase_dates_history = CAST(:history AS jsonb)
        """
        params = {
            "client_id": client_id,
            "product_id": product_id,
            "history": json.dumps(purchase_dates_history)
        }
        
        if previous_last_date:
            update_sql += ", last_purchase_date = CAST(:prev_date AS timestamp)"
            params["prev_date"] = previous_last_date.isoformat()
        else:
            update_sql += ", last_purchase_date = NULL"
        
        update_sql += " WHERE client_id = :client_id AND product_id = :product_id"
        
        db.execute(text(update_sql), params)
        
        # Update client's updated_at
        client.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Purchase decremented successfully",
            "client_id": client_id,
            "product_id": product_id,
            "new_quantity": quantity - 1,
            "previous_last_purchase_date": previous_last_date.isoformat() if previous_last_date else None
        }

@router.post("/create-from-order")
def create_client_from_order(
    order_id: str = Body(..., description="Yandex order ID"),
    email: Optional[str] = Body(None, description="Client email (optional if buyer_id exists)"),
    name: Optional[str] = Body(None, description="Client name (optional, uses order customer name if not provided)"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a client from an order or append order to existing client using buyer_id"""
    import json
    
    business_id = get_business_id(current_user)
    # Get all orders with this yandex_order_id for this business
    orders = db.query(models.Order).filter(
        models.Order.yandex_order_id == order_id,
        models.Order.business_id == business_id
    ).all()
    if not orders:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if a client already exists for this order (prevent duplicates)
    # Query clients and check if order_id is in their order_ids array
    existing_client_for_order = None
    # Use a simple Python check - query only clients that have order_ids for this business
    clients_with_orders = db.query(models.Client).filter(
        models.Client.business_id == business_id,
        models.Client.order_ids.isnot(None)
    ).all()
    for client in clients_with_orders:
        if client.order_ids and isinstance(client.order_ids, list) and order_id in client.order_ids:
            existing_client_for_order = client
            break
    
    if existing_client_for_order:
        raise HTTPException(status_code=400, detail=f"Client already exists for this order. Client ID: {existing_client_for_order.id}")
    
    # Get buyer_id from the first order (all orders from same yandex_order_id have same buyer_id)
    buyer_id = orders[0].buyer_id if orders else None
    
    # Also try to extract buyer_id from yandex_order_data if not in order record
    # This is a fallback in case buyer_id wasn't saved to the order record yet
    if not buyer_id:
        yandex_order_data = orders[0].yandex_order_data or {}
        if isinstance(yandex_order_data, dict):
            buyer = yandex_order_data.get("buyer", {})
            if isinstance(buyer, dict):
                buyer_id = buyer.get("id")
                # If we found buyer_id in yandex_order_data, update the order record for future use
                if buyer_id:
                    for order in orders:
                        order.buyer_id = buyer_id
                    db.flush()
    
    # Check if client already exists by buyer_id (primary method) for this business
    existing_client = None
    if buyer_id:
        existing_client = db.query(models.Client).filter(
            models.Client.buyer_id == buyer_id,
            models.Client.business_id == business_id
        ).first()
        print(f"🔍 Checking for client with buyer_id: {buyer_id}, found: {existing_client is not None}")
    
    # If buyer_id exists and matches a client, auto-append without requiring email
    # This handles both same products and different products - just append to existing client
    if existing_client and buyer_id:
        # Auto-append to existing client - no email needed, proceed directly to appending
        print(f"✅ Auto-appending order {order_id} to existing client {existing_client.id} (buyer_id: {buyer_id})")
        pass
    elif not existing_client:
        # Need to create new client - email is required
        if not email:
            # If buyer_id exists but no client found, we still need email to create new client
            if buyer_id:
                print(f"⚠️  No client found with buyer_id {buyer_id}, email required to create new client")
                raise HTTPException(status_code=400, detail="Email is required when creating a new client. No existing client found with buyer_id.")
            else:
                print(f"⚠️  No buyer_id found for order {order_id}, email required")
                raise HTTPException(status_code=400, detail="Email is required when creating a new client without buyer_id")
        
        # Fallback to email matching if no buyer_id match found
        existing_client = db.query(models.Client).filter(models.Client.email == email).first()
    
    # Get buyer name from Yandex order data if available
    buyer_name = None
    yandex_order_data = orders[0].yandex_order_data or {}
    if isinstance(yandex_order_data, dict):
        buyer = yandex_order_data.get("buyer", {})
        if isinstance(buyer, dict):
            first_name = buyer.get("firstName", "")
            last_name = buyer.get("lastName", "")
            if first_name or last_name:
                buyer_name = f"{first_name} {last_name}".strip()
    
    # Get customer name from order if not provided
    if not name:
        name = buyer_name or orders[0].customer_name or "Unknown Customer"
    
    # Get order creation date (use order_created_at if available, otherwise created_at)
    order_date = orders[0].order_created_at or orders[0].created_at
    if order_date and order_date.tzinfo is None:
        order_date = order_date.replace(tzinfo=timezone.utc)
    
    if existing_client:
        # Auto-append to existing client - no email needed if buyer_id matches
        if buyer_id and existing_client.buyer_id == buyer_id:
            # Use buyer name from Yandex if available
            if buyer_name and buyer_name != "Unknown Customer":
                existing_client.name = buyer_name
        # Update existing client
        # Add order ID if not already present
        order_ids = existing_client.order_ids or []
        if order_id not in order_ids:
            order_ids.append(order_id)
            existing_client.order_ids = order_ids
            # Explicitly mark the JSONB field as modified so SQLAlchemy saves it
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(existing_client, 'order_ids')
        
        # Update products from this order
        for order in orders:
            product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
            if not product:
                continue
            
            # Check if client already has this product
            if product in existing_client.purchased_products:
                # Increment quantity and update purchase history
                result = db.execute(text("""
                    SELECT purchase_dates_history FROM client_products 
                    WHERE client_id = :client_id AND product_id = :product_id
                """), {"client_id": existing_client.id, "product_id": product.id})
                row = result.first()
                
                purchase_dates_history = row[0] if row and row[0] else []
                if isinstance(purchase_dates_history, str):
                    purchase_dates_history = json.loads(purchase_dates_history)
                if not isinstance(purchase_dates_history, list):
                    purchase_dates_history = []
                
                # Add current order date to history
                order_date_str = order_date.isoformat() if order_date else datetime.utcnow().isoformat()
                purchase_dates_history.append(order_date_str)
                
                # Update quantity and purchase history
                db.execute(text("""
                    UPDATE client_products 
                    SET quantity = quantity + :qty,
                        last_purchase_date = CAST(:order_date AS timestamp),
                        purchase_dates_history = CAST(:history AS jsonb)
                    WHERE client_id = :client_id AND product_id = :product_id
                """), {
                    "client_id": existing_client.id,
                    "product_id": product.id,
                    "qty": order.quantity,
                    "order_date": order_date_str,
                    "history": json.dumps(purchase_dates_history)
                })
            else:
                # Add new product to client
                existing_client.purchased_products.append(product)
                db.flush()
                
                # Set initial quantity and purchase history
                order_date_str = order_date.isoformat() if order_date else datetime.utcnow().isoformat()
                purchase_dates_history = [order_date_str]
                
                db.execute(text("""
                    UPDATE client_products 
                    SET quantity = :qty,
                        first_purchase_date = CAST(:order_date AS timestamp),
                        last_purchase_date = CAST(:order_date AS timestamp),
                        purchase_dates_history = CAST(:history AS jsonb)
                    WHERE client_id = :client_id AND product_id = :product_id
                """), {
                    "client_id": existing_client.id,
                    "product_id": product.id,
                    "qty": order.quantity,
                    "order_date": order_date_str,
                    "history": json.dumps(purchase_dates_history)
                })
        
        existing_client.updated_at = datetime.utcnow()
        # Ensure order_ids is saved - explicitly mark as modified for SQLAlchemy
        db.add(existing_client)  # Mark as modified to ensure JSONB field is saved
        db.flush()  # Flush to ensure order_ids is saved before commit
        db.commit()
        db.refresh(existing_client)  # Refresh to get latest data from database
        existing_client.purchased_product_ids = [p.id for p in existing_client.purchased_products]
        if not existing_client.order_ids:
            existing_client.order_ids = []
        _add_product_quantities(existing_client, db)
        return existing_client
    else:
        # Create new client with buyer_id
        # Use buyer name from Yandex if available, otherwise use provided name or customer_name
        client_name = buyer_name if buyer_name and buyer_name != "Unknown Customer" else (name or "Unknown Customer")
        db_client = models.Client(
            name=client_name,
            email=email,
            buyer_id=buyer_id,  # Set buyer_id from order
            order_ids=[order_id],
            business_id=business_id
        )
        db.add(db_client)
        db.flush()
        
        # Add products from order
        for order in orders:
            product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
            if not product:
                continue
            
            db_client.purchased_products.append(product)
            db.flush()
            
            # Set initial quantity and purchase history
            order_date_str = order_date.isoformat() if order_date else datetime.utcnow().isoformat()
            purchase_dates_history = [order_date_str]
            
            db.execute(text("""
                UPDATE client_products 
                SET quantity = :qty,
                    first_purchase_date = CAST(:order_date AS timestamp),
                    last_purchase_date = CAST(:order_date AS timestamp),
                    purchase_dates_history = CAST(:history AS jsonb)
                WHERE client_id = :client_id AND product_id = :product_id
            """), {
                "client_id": db_client.id,
                "product_id": product.id,
                "qty": order.quantity,
                "order_date": order_date_str,
                "history": json.dumps(purchase_dates_history)
            })
        
        db.commit()
        db.refresh(db_client)
        db_client.purchased_product_ids = [p.id for p in db_client.purchased_products]
        if not db_client.order_ids:
            db_client.order_ids = []
        _add_product_quantities(db_client, db)
        return db_client
