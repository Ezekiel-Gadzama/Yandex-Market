from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_ as sql_or, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.auth import get_current_active_user, has_permission, get_business_id
from app.utils.export_utils import (
    extract_text_from_file,
    build_txt_marketing,
    build_pdf_bytes,
    strip_html,
)

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
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all marketing email templates with optional search. Default templates are sorted first. Requires view_marketing_emails permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_marketing_emails"
        )
    business_id = get_business_id(current_user)
    query = db.query(models.MarketingEmailTemplate).filter(models.MarketingEmailTemplate.business_id == business_id)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            sql_or(
                func.lower(models.MarketingEmailTemplate.name).like(search_term),
                func.lower(models.MarketingEmailTemplate.subject).like(search_term),
                func.lower(models.MarketingEmailTemplate.body).like(search_term)
            )
        )
    
    # Sort: default templates first, then by created_at descending
    templates = query.order_by(
        models.MarketingEmailTemplate.is_default.desc(),
        models.MarketingEmailTemplate.created_at.desc()
    ).all()
    
    return templates

@router.post("/", response_model=schemas.MarketingEmailTemplate)
def create_marketing_template(
    template: schemas.MarketingEmailTemplateCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new marketing email template. Requires view_marketing_emails permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_marketing_emails"
        )
    business_id = get_business_id(current_user)
    # Check if trying to create another default template when one already exists for this business
    if template.is_default:
        existing_default = db.query(models.MarketingEmailTemplate).filter(
            models.MarketingEmailTemplate.business_id == business_id,
            models.MarketingEmailTemplate.is_default == True
        ).first()
        if existing_default:
            raise HTTPException(status_code=400, detail="A default template already exists. Only one default template is allowed.")
    
    template_data = template.dict()
    template_data['business_id'] = business_id
    db_template = models.MarketingEmailTemplate(**template_data)
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.post("/from-file", response_model=schemas.MarketingEmailTemplate, status_code=201)
async def create_marketing_template_from_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a marketing email template from a TXT or PDF file. Name and subject from filename; body from file content."""
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(status_code=403, detail="Permission required: view_marketing_emails")
    if not file.filename or not file.filename.lower().endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt or .pdf files are allowed")
    content = await file.read()
    body_text = extract_text_from_file(content, file.filename)
    if not body_text.strip():
        raise HTTPException(status_code=400, detail="File appears empty or could not extract text")
    import os
    base_name = os.path.splitext(file.filename or "template")[0]
    name = base_name.replace("_", " ").replace("-", " ").strip() or "Imported Template"
    # Use first line as subject if multiple lines, else name
    lines = body_text.strip().split("\n")
    subject = lines[0][:200].strip() if lines else name
    body = body_text  # Store as plain text; frontend may show as HTML
    business_id = get_business_id(current_user)
    db_template = models.MarketingEmailTemplate(
        business_id=business_id,
        name=name,
        subject=subject,
        body=f"<p>{body.replace(chr(10), '<br/>')}</p>",
        is_default=False,
        auto_broadcast_enabled=False,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.get("/{template_id}", response_model=schemas.MarketingEmailTemplate)
def get_marketing_template(
    template_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific marketing email template. Requires view_marketing_emails permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_marketing_emails"
        )
    business_id = get_business_id(current_user)
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id,
        models.MarketingEmailTemplate.business_id == business_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/{template_id}/export")
def export_marketing_template(
    template_id: int,
    format: str = Query("txt", regex="^(txt|pdf)$"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Export marketing email template as TXT or PDF."""
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(status_code=403, detail="Permission required: view_marketing_emails")
    business_id = get_business_id(current_user)
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id,
        models.MarketingEmailTemplate.business_id == business_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    full_text = build_txt_marketing(template.name, template.subject or "", template.body or "")
    safe_name = "".join(c for c in template.name if c.isalnum() or c in " -_")[:80].strip() or "marketing-template"
    if format == "pdf":
        pdf_bytes = build_pdf_bytes(template.name, full_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
        )
    return Response(
        content=full_text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.txt"'},
    )


@router.put("/{template_id}", response_model=schemas.MarketingEmailTemplate)
def update_marketing_template(
    template_id: int,
    template_update: schemas.MarketingEmailTemplateUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a marketing email template. Requires view_marketing_emails permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_marketing_emails"
        )
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Prevent changing is_default if trying to set another template as default
    # Get update data - use exclude_unset=True to only include fields that were provided
    update_data = template_update.dict(exclude_unset=True)
    
    # Debug: Log what we received
    print(f"📥 Received update for template {template_id}: {list(update_data.keys())}")
    if 'attachments' in update_data:
        print(f"📎 Attachments in update_data: {update_data['attachments']}")
    else:
        print(f"⚠️  Attachments NOT in update_data")
    
    # Explicitly handle attachments - always include if it was provided in the request
    # Pydantic's exclude_unset=True might exclude empty lists, so we check the raw input
    if hasattr(template_update, 'attachments'):
        # Attachments field exists in the model, include it in update
        update_data['attachments'] = template_update.attachments
        print(f"✅ Including attachments: {template_update.attachments}")
    
    if update_data.get("is_default") and not template.is_default:
        # Check if another default template exists for this business
        existing_default = db.query(models.MarketingEmailTemplate).filter(
            models.MarketingEmailTemplate.business_id == business_id,
            models.MarketingEmailTemplate.is_default == True,
            models.MarketingEmailTemplate.id != template_id
        ).first()
        if existing_default:
            raise HTTPException(status_code=400, detail="A default template already exists. Only one default template is allowed.")
    
    # Debug logging
    if "attachments" in update_data:
        print(f"📎 Updating template {template_id} attachments: {update_data['attachments']}")
    
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    # Debug logging
    print(f"✅ Template {template_id} updated. Attachments: {template.attachments}")
    
    return template

@router.delete("/{template_id}")
def delete_marketing_template(
    template_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a marketing email template. Requires view_marketing_emails permission."""
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_marketing_emails"
        )
    business_id = get_business_id(current_user)
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id,
        models.MarketingEmailTemplate.business_id == business_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Prevent deletion of default template
    if template.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default template")
    
    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}

@router.post("/{template_id}/broadcast")
async def broadcast_marketing_email(
    template_id: int,
    filters: BroadcastFilters,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Broadcast a marketing email with advanced filtering options. Requires view_marketing_emails permission.
    
    For default templates, generates unique emails per client based on expired subscriptions.
    Ensures no duplicate clients are created (checks by email).
    """
    # Check permission
    if not current_user.is_admin and not has_permission(current_user, "view_marketing_emails"):
        raise HTTPException(
            status_code=403,
            detail="Permission required: view_marketing_emails"
        )
    import json
    from sqlalchemy import text
    
    # Get template
    template = db.query(models.MarketingEmailTemplate).filter(
        models.MarketingEmailTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Handle default template broadcast differently
    if template.is_default:
        # Default template: generate unique emails per client based on expired subscriptions
        business_id = get_business_id(current_user)
        all_clients = db.query(models.Client).filter(models.Client.business_id == business_id).all()
        clients_to_email = []
        unique_emails = set()  # Track emails to prevent duplicates
        
        for client in all_clients:
            # Skip if email already processed (prevent duplicates)
            if client.email in unique_emails:
                continue
            
            expired_products = []
            
            # Check each product the client has purchased
            for product in client.purchased_products:
                # Skip if product doesn't have Yandex purchase link, is inactive, or doesn't exist
                if not product.yandex_purchase_link or not product.is_active:
                    continue
                
                # Get purchase history for this product
                result = db.execute(text("""
                    SELECT last_purchase_date, purchase_dates_history FROM client_products 
                    WHERE client_id = :client_id AND product_id = :product_id
                """), {"client_id": client.id, "product_id": product.id})
                row = result.first()
                
                if not row or not row[0]:
                    continue
                
                last_purchase_date = row[0]
                if last_purchase_date and last_purchase_date.tzinfo is None:
                    last_purchase_date = last_purchase_date.replace(tzinfo=datetime.timezone.utc)
                
                # Determine expiry period
                expiry_days = None
                if product.product_type == models.ProductType.PHYSICAL:
                    # For physical products, use usage_period if available
                    expiry_days = product.usage_period
                else:
                    # For digital products, use activation template expiry period
                    if product.email_template_id:
                        business_id = get_business_id(current_user)
                        email_template = db.query(models.EmailTemplate).filter(
                            models.EmailTemplate.id == product.email_template_id,
                            models.EmailTemplate.business_id == business_id
                        ).first()
                        if email_template:
                            expiry_days = email_template.activate_till_days
                
                if not expiry_days:
                    continue  # No expiry period defined, skip
                
                # Check if subscription has expired
                expiry_date = last_purchase_date + timedelta(days=expiry_days)
                if datetime.utcnow().replace(tzinfo=datetime.timezone.utc) > expiry_date:
                    expired_products.append({
                        "product": product,
                        "last_purchase_date": last_purchase_date,
                        "expiry_date": expiry_date,
                        "expiry_days": expiry_days
                    })
            
            # Only add client if they have expired products
            if expired_products:
                clients_to_email.append({
                    "client": client,
                    "expired_products": expired_products
                })
                unique_emails.add(client.email)  # Track email to prevent duplicates
        
        if not clients_to_email:
            raise HTTPException(status_code=400, detail="No clients have expired subscriptions")
        
        # Send emails to clients with expired subscriptions
        from app.services.email_service import EmailService
        from jinja2 import Template as JinjaTemplate
        from app.services.config_validator import ConfigurationError, format_config_error_response
        email_service = EmailService(business_id=business_id, db=db)
        
        sent_count = 0
        failed_count = 0
        failed_emails = []
        
        for client_data in clients_to_email:
            client = client_data["client"]
            expired_products = client_data["expired_products"]
            
            if not client.email:
                print(f"⚠️  Skipping client {client.id} ({client.name}) - no email address")
                continue
            
            # Generate unique email content for this client based on expired products
            # Create a list of expired product names and purchase links
            expired_product_list = []
            for ep in expired_products:
                product = ep["product"]
                expired_product_list.append({
                    "name": product.name,
                    "purchase_link": product.yandex_purchase_link,
                    "expired_date": ep["expiry_date"].strftime("%B %d, %Y") if ep.get("expiry_date") else "N/A"
                })
            
            # Render template with client-specific data
            jinja_template = JinjaTemplate(template.body)
            email_body = jinja_template.render(
                client_name=client.name,
                expired_products=expired_product_list,
                additional_info=template.body  # Include the template body as additional info
            )
            
            # Send email
            result = email_service.send_marketing_email(
                to_email=client.email,
                subject=template.subject,
                body=email_body,
                attachments=template.attachments if hasattr(template, 'attachments') and template.attachments else None
            )
            
            if result.get("success"):
                sent_count += 1
            else:
                failed_count += 1
                failed_emails.append(client.email)
                print(f"⚠️  Failed to send email to {client.email}: {result.get('message', 'Unknown error')}")
        
        response_message = f"Default template broadcast completed: {sent_count} sent"
        if failed_count > 0:
            response_message += f", {failed_count} failed"
        
        return {
            "message": response_message,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "failed_emails": failed_emails if failed_count > 0 else [],
            "template_id": template_id,
            "template_name": template.name,
            "filters_applied": ["expired subscriptions only"],
            "clients_processed": len(clients_to_email),
            "unique_emails": len(unique_emails)
        }
    
    # Regular template broadcast (existing logic)
    # Build query for clients - filter by business_id
    business_id = get_business_id(current_user)
    query = db.query(models.Client).filter(models.Client.business_id == business_id).distinct()
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
    
    # Ensure no duplicate emails (prevent creating duplicate clients)
    unique_emails = set()
    unique_clients = []
    for client in clients:
        if client.email not in unique_emails:
            unique_clients.append(client)
            unique_emails.add(client.email)
    
    clients = unique_clients
    
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
        # Provide more helpful error message
        if filters.product_ids and len(filters.product_ids) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No clients have purchased the selected products. Please select different products or send to all clients."
            )
        elif filters.min_total_products and filters.min_total_products > 1:
            raise HTTPException(
                status_code=400,
                detail=f"No clients have purchased at least {filters.min_total_products} different products. Please adjust the minimum total products filter."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="No clients match the criteria. Please check your filters or ensure you have clients in the system."
            )
    
    # Send emails to all matching clients
    from app.services.email_service import EmailService
    from app.services.config_validator import ConfigurationError, format_config_error_response
    email_service = EmailService(business_id=business_id, db=db)
    
    sent_count = 0
    failed_count = 0
    failed_emails = []
    
    for client in clients:
        if not client.email:
            print(f"⚠️  Skipping client {client.id} ({client.name}) - no email address")
            continue
        
        # Send email
        result = email_service.send_marketing_email(
            to_email=client.email,
            subject=template.subject,
            body=template.body,
            attachments=template.attachments if hasattr(template, 'attachments') and template.attachments else None
        )
        
        if result.get("success"):
            sent_count += 1
        else:
            failed_count += 1
            failed_emails.append(client.email)
            print(f"⚠️  Failed to send email to {client.email}: {result.get('message', 'Unknown error')}")
    
    filter_msg = f" ({', '.join(filter_descriptions)})" if filter_descriptions else ""
    
    response_message = f"Email broadcast completed: {sent_count} sent"
    if failed_count > 0:
        response_message += f", {failed_count} failed"
    
    return {
        "message": response_message,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "failed_emails": failed_emails if failed_count > 0 else [],
        "template_id": template_id,
        "template_name": template.name,
        "filters_applied": filter_descriptions,
        "unique_emails": len(unique_emails)  # Confirm no duplicates
    }
