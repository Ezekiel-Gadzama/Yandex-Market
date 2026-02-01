from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import json
from app.database import get_db
from app import models, schemas
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


@router.post("/", response_model=schemas.SyncResult)
def sync_all(force: bool = False, db: Session = Depends(get_db)):
    """
    Sync all data FROM Yandex Market TO local database (one-way sync)
    
    This syncs both products and orders.
    - force=True: Syncs all items even if already synced
    - force=False: Only syncs items that aren't already synced
    """
    try:
        # Sync products
        products_result = sync_products(force=force, db=db)
        
        # Sync orders
        orders_result = sync_orders(db=db)
        
        return schemas.SyncResult(
            success=True,
            products_synced=products_result.products_synced,
            products_created=products_result.products_created,
            products_updated=products_result.products_updated,
            products_pushed=0,
            errors=products_result.errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/products", response_model=schemas.SyncResult)
def sync_products(force: bool = False, db: Session = Depends(get_db)):
    """
    Sync products FROM Yandex Market TO local database (one-way sync)
    
    Yandex Market is the source of truth. This sync:
    - Pulls all products from Yandex Market
    - Updates local database to match Yandex exactly
    - Preserves only local-only fields (cost_price, supplier info) that don't exist in Yandex
    """
    try:
        yandex_api = YandexMarketAPI()
        yandex_products = yandex_api.get_products()
        
        products_synced = 0
        products_created = 0
        products_updated = 0
        errors = []
        
        for yandex_product in yandex_products:
            try:
                yandex_id = yandex_product.get("id")
                yandex_sku = yandex_product.get("sku")
                
                # Check if product exists by Yandex Market ID or SKU
                existing_product = db.query(models.Product).filter(
                    (models.Product.yandex_market_id == yandex_id) |
                    (models.Product.yandex_market_sku == yandex_sku)
                ).first()
                
                if existing_product:
                    if force or not existing_product.is_synced:
                        # Preserve ONLY local-only fields that don't exist in Yandex
                        preserved_cost_price = existing_product.cost_price
                        preserved_supplier_url = existing_product.supplier_url
                        preserved_supplier_name = existing_product.supplier_name
                        preserved_email_template_id = existing_product.email_template_id
                        
                        # Download and save media from Yandex
                        media_dir = Path("media")
                        try:
                            downloaded_images, downloaded_videos = yandex_api.download_product_media(
                                yandex_product, media_dir
                            )
                            # Merge with existing media (don't overwrite, append new)
                            existing_images = []
                            existing_videos = []
                            if existing_product.yandex_images:
                                try:
                                    existing_images = json.loads(existing_product.yandex_images) if isinstance(existing_product.yandex_images, str) else existing_product.yandex_images
                                except:
                                    existing_images = []
                            if existing_product.yandex_videos:
                                try:
                                    existing_videos = json.loads(existing_product.yandex_videos) if isinstance(existing_product.yandex_videos, str) else existing_product.yandex_videos
                                except:
                                    existing_videos = []
                            
                            # Combine existing and new media (avoid duplicates)
                            all_images = list(set(existing_images + downloaded_images))
                            all_videos = list(set(existing_videos + downloaded_videos))
                            existing_product.yandex_images = json.dumps(all_images) if all_images else None
                            existing_product.yandex_videos = json.dumps(all_videos) if all_videos else None
                        except Exception as e:
                            errors.append(f"Failed to download media for product {yandex_id}: {str(e)}")
                        
                        # Update ALL Yandex fields to match Yandex exactly
                        existing_product.name = yandex_product.get("name", existing_product.name)
                        existing_product.description = yandex_product.get("description", existing_product.description)
                        existing_product.selling_price = yandex_product.get("price", existing_product.selling_price)
                        existing_product.yandex_market_id = yandex_id
                        existing_product.yandex_market_sku = yandex_sku
                        
                        # Update active status from Yandex
                        availability = yandex_product.get("availability", "")
                        if availability:
                            existing_product.is_active = (availability == "ACTIVE")
                        
                        # Restore preserved local-only fields
                        existing_product.cost_price = preserved_cost_price
                        existing_product.supplier_url = preserved_supplier_url
                        existing_product.supplier_name = preserved_supplier_name
                        existing_product.email_template_id = preserved_email_template_id
                        
                        existing_product.is_synced = True
                        products_updated += 1
                else:
                    # Create new product from Yandex
                    new_product = models.Product(
                        name=yandex_product.get("name", "Unknown Product"),
                        description=yandex_product.get("description"),
                        yandex_market_id=yandex_id,
                        yandex_market_sku=yandex_sku,
                        selling_price=yandex_product.get("price", 0),
                        cost_price=0,  # Will need to be set manually
                        is_synced=True,
                        product_type=models.ProductType.DIGITAL  # Default, can be updated
                    )
                    
                    # Download and save media from Yandex
                    media_dir = Path("media")
                    try:
                        downloaded_images, downloaded_videos = yandex_api.download_product_media(
                            yandex_product, media_dir
                        )
                        new_product.yandex_images = json.dumps(downloaded_images) if downloaded_images else None
                        new_product.yandex_videos = json.dumps(downloaded_videos) if downloaded_videos else None
                    except Exception as e:
                        errors.append(f"Failed to download media for new product {yandex_id}: {str(e)}")
                    
                    # Set active status from Yandex
                    availability = yandex_product.get("availability", "")
                    if availability:
                        new_product.is_active = (availability == "ACTIVE")
                    
                    db.add(new_product)
                    products_created += 1
                
                products_synced += 1
            except Exception as e:
                errors.append(f"Error syncing product {yandex_product.get('id')}: {str(e)}")
        
        db.commit()
        
        return schemas.SyncResult(
            success=True,
            products_synced=products_synced,
            products_created=products_created,
            products_updated=products_updated,
            products_pushed=0,  # Sync is one-way: Yandex → Local
            errors=errors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/orders", response_model=dict)
def sync_orders(db: Session = Depends(get_db)):
    """Sync orders from Yandex Market"""
    try:
        yandex_api = YandexMarketAPI()
        yandex_orders = yandex_api.get_orders()
        
        orders_created = 0
        orders_updated = 0
        
        for yandex_order in yandex_orders:
            try:
                existing_order = db.query(models.Order).filter(
                    models.Order.yandex_order_id == str(yandex_order.get("id"))
                ).first()
                
                if not existing_order:
                    # Find product by Yandex Market SKU or ID
                    product = db.query(models.Product).filter(
                        (models.Product.yandex_market_sku == yandex_order.get("sku")) |
                        (models.Product.yandex_market_id == str(yandex_order.get("productId")))
                    ).first()
                    
                    if product:
                        new_order = models.Order(
                            yandex_order_id=str(yandex_order.get("id")),
                            product_id=product.id,
                            customer_name=yandex_order.get("customer", {}).get("name"),
                            customer_email=yandex_order.get("customer", {}).get("email"),
                            customer_phone=yandex_order.get("customer", {}).get("phone"),
                            quantity=yandex_order.get("quantity", 1),
                            total_amount=yandex_order.get("totalAmount", 0),
                            status=models.OrderStatus.PENDING
                        )
                        db.add(new_order)
                        orders_created += 1
            except Exception as e:
                continue
        
        db.commit()
        
        return {
            "success": True,
            "orders_created": orders_created,
            "orders_updated": orders_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order sync failed: {str(e)}")
