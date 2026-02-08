from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_ as sql_or, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas

router = APIRouter()

# Pydantic model for broadcast filters
class BroadcastFilters(BaseModel):
    product_ids: Optional[List[int]] = None
    date_filter: Optional[str] = None  # 'last_month', 'last_3_months', 'last_6_months', 'last_year', 'custom'
    custom_start_date: Optional[str] = None  # ISO format date string
    custom_end_date: Optional[str] = None  # ISO format date string
    min_product_quantity: Optional[int] = None  # Minimum quantity of specific product
    min_total_products: Optional[int] = None  # Minimum total number of different products bought

@router.get("/", response_model=List[schemas.MarketingEmailTemplate])
def get_marketing_templates(
    search: str = Query(None, description="Search by name, subject, or body"),
    db: Session = Depends(get_db)
):
    """Get all marketing email templates with optional search"""
    query = db.query(models.MarketingEmailTemplate)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            sql_or(
                func.lower(models.MarketingEmailTemplate.name).like(search_term),
                func.lower(models.MarketingEmailTemplate.subject).like(search_term),
                func.lower(models.MarketingEmailTemplate.body).like(search_term)
            )
        )
    
    return query.all()

@router.post("/", response_model=schemas.MarketingEmailTemplate)
def create_marketing_template(
    template: schemas.MarketingEmailTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new marketing email template"""
    db_template = models.MarketingEmailTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.get("/{template_id}", response_model=schemas.MarketingEmailTemplate)
def get_marketing_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific marketing email template"""
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/{template_id}", response_model=schemas.MarketingEmailTemplate)
def update_marketing_template(
    template_id: int,
    template_update: schemas.MarketingEmailTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a marketing email template"""
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    return template

@router.delete("/{template_id}")
def delete_marketing_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a marketing email template"""
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}

@router.post("/{template_id}/broadcast")
async def broadcast_marketing_email(
    template_id: int,
    filters: BroadcastFilters,
    db: Session = Depends(get_db)
):
    """Broadcast a marketing email with advanced filtering options"""
    # Get template
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Build query for clients
    query = db.query(models.Client).distinct()
    filter_descriptions = []
    
    # Apply product filter
    if filters.product_ids and len(filters.product_ids) > 0:
        query = query.join(models.Client.purchased_products).filter(
            models.Product.id.in_(filters.product_ids)
        )
        filter_descriptions.append(f"{len(filters.product_ids)} product(s)")
    
    # Apply date filter
    if filters.date_filter or (filters.custom_start_date and filters.custom_end_date):
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = None
        
        if filters.date_filter == 'last_month':
            start_date = end_date - timedelta(days=30)
            filter_descriptions.append("last month")
        elif filters.date_filter == 'last_3_months':
            start_date = end_date - timedelta(days=90)
            filter_descriptions.append("last 3 months")
        elif filters.date_filter == 'last_6_months':
            start_date = end_date - timedelta(days=180)
            filter_descriptions.append("last 6 months")
        elif filters.date_filter == 'last_year':
            start_date = end_date - timedelta(days=365)
            filter_descriptions.append("last year")
        elif filters.date_filter == 'custom' and filters.custom_start_date and filters.custom_end_date:
            start_date = datetime.fromisoformat(filters.custom_start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(filters.custom_end_date.replace('Z', '+00:00'))
            filter_descriptions.append(f"{start_date.date()} to {end_date.date()}")
        
        if start_date:
            # Filter by updated_at (when client was last updated)
            query = query.filter(models.Client.updated_at >= start_date)
            query = query.filter(models.Client.updated_at <= end_date)
    
    # Get clients matching criteria so far
    clients = query.all()
    
    # Apply quantity filters (these require raw SQL queries)
    if filters.min_product_quantity is not None and filters.product_ids:
        # Filter clients who bought at least N of any specified product
        filtered_clients = []
        for client in clients:
            for product_id in filters.product_ids:
                result = db.execute(text("""
                    SELECT quantity FROM client_products 
                    WHERE client_id = :client_id AND product_id = :product_id AND quantity >= :min_qty
                """), {"client_id": client.id, "product_id": product_id, "min_qty": filters.min_product_quantity})
                if result.scalar():
                    filtered_clients.append(client)
                    break
        clients = filtered_clients
        filter_descriptions.append(f"bought {filters.min_product_quantity}+ of selected products")
    
    if filters.min_total_products is not None:
        # Filter clients who bought at least N different products
        filtered_clients = []
        for client in clients:
            if len(client.purchased_products) >= filters.min_total_products:
                filtered_clients.append(client)
        clients = filtered_clients
        filter_descriptions.append(f"{filters.min_total_products}+ different products")
    
    if not clients:
        raise HTTPException(status_code=400, detail="No clients match the criteria")
    
    # TODO: Implement actual email sending logic here
    
    filter_msg = f" ({', '.join(filter_descriptions)})" if filter_descriptions else ""
    sent_count = len(clients)
    
    return {
        "message": f"Email broadcast initiated to {sent_count} clients{filter_msg}",
        "sent_count": sent_count,
        "template_id": template_id,
        "template_name": template.name,
        "filters_applied": filter_descriptions
    }
