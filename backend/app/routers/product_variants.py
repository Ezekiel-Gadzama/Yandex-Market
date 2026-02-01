"""
Product Variants Management
Handles products with multiple options/variants (e.g., different editions, platforms, territories)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from app.database import get_db
from app import models, schemas
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


@router.get("/products/{product_id}/variants", response_model=List[schemas.ProductVariant])
def get_product_variants(product_id: int, db: Session = Depends(get_db)):
    """Get all variants for a product"""
    variants = db.query(models.ProductVariant).filter(
        models.ProductVariant.product_id == product_id
    ).order_by(models.ProductVariant.created_at.desc()).all()
    return variants


@router.post("/products/{product_id}/variants", response_model=schemas.ProductVariant, status_code=status.HTTP_201_CREATED)
def create_product_variant(
    product_id: int,
    variant: schemas.ProductVariantCreate,
    db: Session = Depends(get_db)
):
    """Create a new variant for a product"""
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create variant
    variant_data = variant.dict()
    variant_data["product_id"] = product_id
    
    # Generate variant SKU if not provided
    if not variant_data.get("variant_sku"):
        variant_data["variant_sku"] = f"{product.yandex_market_sku or product.id}-VAR-{len(db.query(models.ProductVariant).filter(models.ProductVariant.product_id == product_id).all()) + 1}"
    
    db_variant = models.ProductVariant(**variant_data)
    db.add(db_variant)
    db.commit()
    db.refresh(db_variant)
    
    return db_variant


@router.put("/variants/{variant_id}", response_model=schemas.ProductVariant)
def update_product_variant(
    variant_id: int,
    variant_update: schemas.ProductVariantUpdate,
    db: Session = Depends(get_db)
):
    """Update a product variant"""
    db_variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).first()
    if not db_variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    update_data = variant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_variant, field, value)
    
    db.commit()
    db.refresh(db_variant)
    return db_variant


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_variant(variant_id: int, db: Session = Depends(get_db)):
    """Delete a product variant"""
    db_variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).first()
    if not db_variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    db.delete(db_variant)
    db.commit()
    return None


@router.post("/variants/{variant_id}/sync-to-yandex", response_model=dict)
def sync_variant_to_yandex(variant_id: int, db: Session = Depends(get_db)):
    """Sync a variant to Yandex Market as a separate product"""
    db_variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).first()
    if not db_variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    product = db.query(models.Product).filter(models.Product.id == db_variant.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        yandex_api = YandexMarketAPI()
        
        # Create a temporary product model from variant for API call
        variant_product = models.Product(
            name=f"{product.name} - {db_variant.variant_name}",
            description=product.description,
            product_type=product.product_type,
            selling_price=db_variant.selling_price,
            cost_price=db_variant.cost_price,
            yandex_market_sku=db_variant.variant_sku,
            yandex_brand=product.yandex_brand,
            yandex_platform=db_variant.platform or product.yandex_platform,
            yandex_localization=db_variant.localization or product.yandex_localization,
            yandex_edition=db_variant.edition,
            yandex_activation_territory=db_variant.activation_territory or product.yandex_activation_territory,
            yandex_model=product.yandex_model,
            is_active=db_variant.is_active,
            original_price=db_variant.original_price,
            yandex_images=product.yandex_images,
            yandex_videos=product.yandex_videos,
        )
        
        result = yandex_api.create_product(variant_product)
        
        # Update variant with Yandex ID
        if result.get("result", {}).get("offerMappingEntry", {}).get("offer", {}).get("id"):
            db_variant.yandex_market_id = result["result"]["offerMappingEntry"]["offer"]["id"]
            db_variant.yandex_market_sku = result["result"]["offerMappingEntry"]["offer"].get("shopSku", db_variant.variant_sku)
            db_variant.is_synced = True
            db.commit()
        
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync variant to Yandex: {str(e)}")
