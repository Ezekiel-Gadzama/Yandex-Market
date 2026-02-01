"""
Inventory and Stock Management endpoints
For managing product stock, prices, and availability separately via API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.database import get_db
from app import models
from app.services.yandex_api import YandexMarketAPI

router = APIRouter()


@router.put("/products/{product_id}/stock")
def update_product_stock(
    product_id: int,
    count: int,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update product stock/quantity on Yandex Market"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.yandex_market_sku:
        raise HTTPException(status_code=400, detail="Product not synced with Yandex Market")
    
    try:
        yandex_api = YandexMarketAPI()
        result = yandex_api.update_product_stock(product.yandex_market_sku, count, warehouse_id)
        
        # Update local database
        product.stock_quantity = count
        if warehouse_id:
            product.warehouse_id = warehouse_id
        db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update stock: {str(e)}")


@router.put("/products/bulk/stock")
def update_bulk_stocks(
    stocks: List[Dict[str, int]],
    db: Session = Depends(get_db)
):
    """Update stock for multiple products at once"""
    try:
        yandex_api = YandexMarketAPI()
        result = yandex_api.update_bulk_stocks(stocks)
        
        # Update local database
        for stock_data in stocks:
            product = db.query(models.Product).filter(
                models.Product.yandex_market_sku == stock_data["sku"]
            ).first()
            if product:
                product.stock_quantity = stock_data["count"]
        db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bulk stocks: {str(e)}")


@router.get("/products/{product_id}/stock")
def get_product_stock(product_id: int, db: Session = Depends(get_db)):
    """Get current stock/quantity for a product"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.yandex_market_sku:
        return {"stock": product.stock_quantity, "source": "local"}
    
    try:
        yandex_api = YandexMarketAPI()
        yandex_stock = yandex_api.get_product_stock(product.yandex_market_sku)
        return {"stock": yandex_stock.get("count", product.stock_quantity), "source": "yandex", "yandex_data": yandex_stock}
    except Exception as e:
        # Return local stock if Yandex API fails
        return {"stock": product.stock_quantity, "source": "local", "error": str(e)}


@router.put("/products/{product_id}/price")
def update_product_price(
    product_id: int,
    price: float,
    old_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Update product price on Yandex Market"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.yandex_market_sku:
        raise HTTPException(status_code=400, detail="Product not synced with Yandex Market")
    
    try:
        yandex_api = YandexMarketAPI()
        result = yandex_api.update_product_price(product.yandex_market_sku, price, old_price)
        
        # Update local database
        product.selling_price = price
        if old_price:
            product.original_price = old_price
        db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update price: {str(e)}")


@router.put("/products/bulk/price")
def update_bulk_prices(
    prices: List[Dict[str, float]],
    db: Session = Depends(get_db)
):
    """Update prices for multiple products at once"""
    try:
        yandex_api = YandexMarketAPI()
        result = yandex_api.update_bulk_prices(prices)
        
        # Update local database
        for price_data in prices:
            product = db.query(models.Product).filter(
                models.Product.yandex_market_sku == price_data["sku"]
            ).first()
            if product:
                product.selling_price = price_data["price"]
                if "old_price" in price_data:
                    product.original_price = price_data["old_price"]
        db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bulk prices: {str(e)}")


@router.put("/products/{product_id}/availability")
def update_product_availability(
    product_id: int,
    available: bool,
    db: Session = Depends(get_db)
):
    """Update product availability/visibility on storefront"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.yandex_market_sku:
        raise HTTPException(status_code=400, detail="Product not synced with Yandex Market")
    
    try:
        yandex_api = YandexMarketAPI()
        result = yandex_api.update_product_availability(product.yandex_market_sku, available)
        
        # Update local database
        product.is_active = available
        db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update availability: {str(e)}")
