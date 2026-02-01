from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from app.database import get_db
from app import models, schemas
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


def _convert_product_json_fields(product: models.Product) -> dict:
    """Convert JSON string fields to lists for API response"""
    product_dict = {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "product_type": product.product_type,
        "cost_price": product.cost_price,
        "selling_price": product.selling_price,
        "supplier_url": product.supplier_url,
        "supplier_name": product.supplier_name,
        "yandex_market_id": product.yandex_market_id,
        "yandex_market_sku": product.yandex_market_sku,
        "email_template_id": product.email_template_id,
        "is_active": product.is_active,
        "is_synced": product.is_synced,
        "profit": product.profit,
        "profit_percentage": product.profit_percentage,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        # Yandex fields
        "yandex_model": product.yandex_model,
        "yandex_category_id": product.yandex_category_id,
        "yandex_category_path": product.yandex_category_path,
        "yandex_brand": product.yandex_brand,
        "yandex_platform": product.yandex_platform,
        "yandex_localization": product.yandex_localization,
        "yandex_publication_type": product.yandex_publication_type,
        "yandex_activation_territory": product.yandex_activation_territory,
        "yandex_edition": product.yandex_edition,
        "yandex_series": product.yandex_series,
        "yandex_age_restriction": product.yandex_age_restriction,
        "yandex_activation_instructions": product.yandex_activation_instructions,
        "original_price": product.original_price,
        "discount_percentage": product.discount_percentage,
    }
    
    # Convert JSON strings to lists and convert paths to URLs
    if product.yandex_images:
        try:
            image_paths = json.loads(product.yandex_images) if isinstance(product.yandex_images, str) else product.yandex_images
            # Convert paths to URLs
            product_dict["yandex_images"] = [f"/api/media/files/{path}" if not path.startswith("http") and not path.startswith("/") else path for path in image_paths]
        except:
            product_dict["yandex_images"] = []
    else:
        product_dict["yandex_images"] = []
    
    if product.yandex_videos:
        try:
            video_paths = json.loads(product.yandex_videos) if isinstance(product.yandex_videos, str) else product.yandex_videos
            # Convert paths to URLs
            product_dict["yandex_videos"] = [f"/api/media/files/{path}" if not path.startswith("http") and not path.startswith("/") else path for path in video_paths]
        except:
            product_dict["yandex_videos"] = []
    else:
        product_dict["yandex_videos"] = []
    
    return product_dict


@router.get("/", response_model=List[schemas.Product])
def get_products(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    product_type: str = None,
    db: Session = Depends(get_db)
):
    """Get all products with optional filters"""
    query = db.query(models.Product)
    
    if is_active is not None:
        query = query.filter(models.Product.is_active == is_active)
    
    if product_type:
        query = query.filter(models.Product.product_type == product_type)
    
    products = query.offset(skip).limit(limit).all()
    return [_convert_product_json_fields(p) for p in products]


@router.get("/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _convert_product_json_fields(product)


@router.get("/{product_id}/full", response_model=dict)
def get_product_full_details(product_id: int, db: Session = Depends(get_db)):
    """Get full product details including all fields and media"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get full product data
    product_dict = _convert_product_json_fields(product)
    
    # If product is synced with Yandex, try to get additional details from Yandex API
    if product.is_synced and product.yandex_market_id:
        try:
            yandex_api = YandexMarketAPI()
            yandex_products = yandex_api.get_products()
            
            # Find matching product in Yandex
            for yandex_product in yandex_products:
                if (yandex_product.get("id") == product.yandex_market_id or 
                    yandex_product.get("sku") == product.yandex_market_sku):
                    # Merge Yandex data (Yandex is source of truth for synced products)
                    product_dict.update({
                        "yandex_full_data": yandex_product,
                        "yandex_pictures": yandex_product.get("pictures", []),
                        "yandex_videos": yandex_product.get("videos", []),
                        "yandex_params": yandex_product.get("params", {}),
                    })
                    break
        except Exception as e:
            # If Yandex API fails, just return local data
            print(f"Failed to get Yandex product details: {str(e)}")
    
    return product_dict


@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    product_data = product.dict()
    
    # Convert images/videos lists to JSON strings for storage
    # Convert URLs back to paths if they're local media URLs
    if product_data.get("yandex_images"):
        image_paths = product_data["yandex_images"]
        # Convert /api/media/files/ URLs back to relative paths
        image_paths = [path.replace("/api/media/files/", "") if path.startswith("/api/media/files/") else path for path in image_paths]
        product_data["yandex_images"] = json.dumps(image_paths)
    if product_data.get("yandex_videos"):
        video_paths = product_data["yandex_videos"]
        # Convert /api/media/files/ URLs back to relative paths
        video_paths = [path.replace("/api/media/files/", "") if path.startswith("/api/media/files/") else path for path in video_paths]
        product_data["yandex_videos"] = json.dumps(video_paths)
    
    # Ensure digital products use DBS model
    if product_data.get("product_type") == models.ProductType.DIGITAL:
        if not product_data.get("yandex_model"):
            product_data["yandex_model"] = "DBS"
    
    db_product = models.Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return _convert_product_json_fields(db_product)


@router.put("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a product from admin dashboard
    
    Process:
    1. Update local database
    2. If product is synced with Yandex, push changes to Yandex
    3. Immediately sync back from Yandex to get confirmed values
    4. Result: Local and Yandex have the same values
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product is synced with Yandex
    is_synced = db_product.is_synced and db_product.yandex_market_id is not None
    
    # Update local database first
    update_data = product_update.dict(exclude_unset=True)
    
    # Convert images/videos lists to JSON strings for storage
    # Convert URLs back to paths if they're local media URLs
    if "yandex_images" in update_data and update_data["yandex_images"]:
        image_paths = update_data["yandex_images"]
        # Convert /api/media/files/ URLs back to relative paths
        image_paths = [path.replace("/api/media/files/", "") if isinstance(path, str) and path.startswith("/api/media/files/") else path for path in image_paths]
        update_data["yandex_images"] = json.dumps(image_paths)
    if "yandex_videos" in update_data and update_data["yandex_videos"]:
        video_paths = update_data["yandex_videos"]
        # Convert /api/media/files/ URLs back to relative paths
        video_paths = [path.replace("/api/media/files/", "") if isinstance(path, str) and path.startswith("/api/media/files/") else path for path in video_paths]
        update_data["yandex_videos"] = json.dumps(video_paths)
    
    # Ensure digital products use DBS model
    if db_product.product_type == models.ProductType.DIGITAL:
        if "yandex_model" not in update_data or not update_data.get("yandex_model"):
            update_data["yandex_model"] = "DBS"
    
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    # If product is synced with Yandex, push changes and sync back
    if is_synced:
        try:
            yandex_api = YandexMarketAPI()
            
            # Check if any Yandex-relevant fields changed
            yandex_fields = [
                'name', 'description', 'selling_price', 'is_active',
                'yandex_model', 'yandex_category_id', 'yandex_category_path',
                'yandex_brand', 'yandex_platform', 'yandex_localization',
                'yandex_publication_type', 'yandex_activation_territory',
                'yandex_edition', 'yandex_series', 'yandex_age_restriction',
                'yandex_activation_instructions', 'original_price', 'discount_percentage',
                'yandex_images', 'yandex_videos'
            ]
            has_yandex_changes = any(field in update_data for field in yandex_fields)
            
            if has_yandex_changes:
                # Step 1: Push update to Yandex
                yandex_api.update_product(db_product)
                
                # Step 2: Immediately sync back from Yandex to get confirmed values
                # This ensures local and Yandex have exactly the same values
                yandex_products = yandex_api.get_products()
                for yandex_product in yandex_products:
                    if (yandex_product.get("id") == db_product.yandex_market_id or 
                        yandex_product.get("sku") == db_product.yandex_market_sku):
                        # Preserve local-only fields
                        preserved_cost_price = db_product.cost_price
                        preserved_supplier_url = db_product.supplier_url
                        preserved_supplier_name = db_product.supplier_name
                        preserved_email_template_id = db_product.email_template_id
                        
                        # Update with confirmed values from Yandex (Yandex is source of truth)
                        db_product.name = yandex_product.get("name", db_product.name)
                        db_product.description = yandex_product.get("description", db_product.description)
                        db_product.selling_price = yandex_product.get("price", db_product.selling_price)
                        db_product.yandex_market_id = yandex_product.get("id")
                        db_product.yandex_market_sku = yandex_product.get("sku")
                        
                        # Update active status from Yandex
                        availability = yandex_product.get("availability", "")
                        if availability:
                            db_product.is_active = (availability == "ACTIVE")
                        
                        # Restore preserved local-only fields
                        db_product.cost_price = preserved_cost_price
                        db_product.supplier_url = preserved_supplier_url
                        db_product.supplier_name = preserved_supplier_name
                        db_product.email_template_id = preserved_email_template_id
                        
                        db_product.is_synced = True
                        break
        except Exception as e:
            # If Yandex update fails, still save local changes but mark as not synced
            db_product.is_synced = False
            db.commit()
            db.refresh(db_product)
            raise HTTPException(
                status_code=500, 
                detail=f"Product updated locally but failed to sync to Yandex: {str(e)}"
            )
    
    db.commit()
    db.refresh(db_product)
    return _convert_product_json_fields(db_product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product (soft delete by setting is_active=False)"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.is_active = False
    db.commit()
    return None


@router.post("/{product_id}/upload-to-yandex", response_model=dict)
def upload_product_to_yandex(product_id: int, db: Session = Depends(get_db)):
    """Upload product to Yandex Market via API"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        yandex_api = YandexMarketAPI()
        result = yandex_api.create_product(product)
        
        # Update product with Yandex Market IDs
        if result.get("id"):
            product.yandex_market_id = result["id"]
            product.yandex_market_sku = result.get("sku")
            product.is_synced = True
            db.commit()
        
        return {"success": True, "message": "Product uploaded successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload product: {str(e)}")


@router.post("/{product_id}/generate-keys", response_model=dict)
def generate_activation_keys(
    product_id: int,
    count: int = 10,
    db: Session = Depends(get_db)
):
    """Generate activation keys for a product"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.product_type != models.ProductType.DIGITAL:
        raise HTTPException(status_code=400, detail="Only digital products can have activation keys")
    
    import secrets
    keys_created = []
    
    for _ in range(count):
        # Generate a unique key
        key = f"{product.yandex_market_sku or product.id}-{secrets.token_urlsafe(16)}"
        
        # Check if key already exists
        existing = db.query(models.ActivationKey).filter(models.ActivationKey.key == key).first()
        if existing:
            continue
        
        activation_key = models.ActivationKey(
            product_id=product_id,
            key=key
        )
        db.add(activation_key)
        keys_created.append(key)
    
    db.commit()
    return {"success": True, "keys_created": len(keys_created), "keys": keys_created}
