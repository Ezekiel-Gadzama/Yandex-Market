from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.database import get_db
from app.services.yandex_api import YandexMarketAPI
from app.services.telegram_bot import telegram_bot
import asyncio

router = APIRouter()


class ReplyRequest(BaseModel):
    text: str


@router.get("/products", response_model=Dict)
def get_product_reviews(
    product_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get product reviews from Yandex Market with ratings"""
    try:
        yandex_api = YandexMarketAPI()
        reviews = yandex_api.get_product_reviews(product_id=product_id, limit=limit)
        
        # Calculate average rating if reviews exist
        if reviews:
            ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            return {
                "reviews": reviews,
                "average_rating": round(avg_rating, 2),
                "total_reviews": len(reviews),
                "rating_breakdown": _calculate_rating_breakdown(reviews)
            }
        return {"reviews": [], "average_rating": 0, "total_reviews": 0, "rating_breakdown": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product reviews: {str(e)}")


def _calculate_rating_breakdown(reviews: List[Dict]) -> Dict:
    """Calculate rating breakdown (5 stars, 4 stars, etc.)"""
    breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for review in reviews:
        rating = review.get("rating", 0)
        if 1 <= rating <= 5:
            breakdown[int(rating)] += 1
    return breakdown


@router.get("/products/{product_id}/rating", response_model=Dict)
def get_product_rating(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Get product rating summary"""
    try:
        yandex_api = YandexMarketAPI()
        reviews = yandex_api.get_product_reviews(product_id=product_id, limit=100)
        
        if not reviews:
            return {
                "average_rating": 0,
                "total_reviews": 0,
                "rating_breakdown": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            }
        
        ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            "average_rating": round(avg_rating, 2),
            "total_reviews": len(reviews),
            "rating_breakdown": _calculate_rating_breakdown(reviews)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product rating: {str(e)}")


@router.post("/products/{review_id}/reply", response_model=Dict)
def reply_to_product_review(
    review_id: str,
    reply: ReplyRequest,
    db: Session = Depends(get_db)
):
    """Reply to a product review and send Telegram notification"""
    try:
        yandex_api = YandexMarketAPI()
        
        # Get review details before replying
        reviews = yandex_api.get_product_reviews(limit=100)
        review_data = next((r for r in reviews if r.get("id") == review_id), None)
        
        # Send reply
        result = yandex_api.reply_to_review(review_id, reply.text)
        
        # Send Telegram notification
        if telegram_bot and review_data:
            asyncio.create_task(
                telegram_bot.send_review_reply_notification(
                    review_data, reply.text, "product"
                )
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reply to review: {str(e)}")


@router.get("/shop", response_model=Dict)
def get_shop_reviews(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get shop reviews from Yandex Market with ratings"""
    try:
        yandex_api = YandexMarketAPI()
        reviews = yandex_api.get_shop_reviews(limit=limit)
        
        # Calculate average rating
        if reviews:
            ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            return {
                "reviews": reviews,
                "average_rating": round(avg_rating, 2),
                "total_reviews": len(reviews),
                "rating_breakdown": _calculate_rating_breakdown(reviews)
            }
        return {"reviews": [], "average_rating": 0, "total_reviews": 0, "rating_breakdown": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get shop reviews: {str(e)}")


@router.get("/shop/rating", response_model=Dict)
def get_shop_rating(db: Session = Depends(get_db)):
    """Get shop rating summary"""
    try:
        yandex_api = YandexMarketAPI()
        reviews = yandex_api.get_shop_reviews(limit=100)
        
        if not reviews:
            return {
                "average_rating": 0,
                "total_reviews": 0,
                "rating_breakdown": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            }
        
        ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            "average_rating": round(avg_rating, 2),
            "total_reviews": len(reviews),
            "rating_breakdown": _calculate_rating_breakdown(reviews)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get shop rating: {str(e)}")


@router.post("/shop/{review_id}/reply", response_model=Dict)
def reply_to_shop_review(
    review_id: str,
    reply: ReplyRequest,
    db: Session = Depends(get_db)
):
    """Reply to a shop review and send Telegram notification"""
    try:
        yandex_api = YandexMarketAPI()
        
        # Get review details before replying
        reviews = yandex_api.get_shop_reviews(limit=100)
        review_data = next((r for r in reviews if r.get("id") == review_id), None)
        
        # Send reply
        result = yandex_api.reply_to_shop_review(review_id, reply.text)
        
        # Send Telegram notification
        if telegram_bot and review_data:
            asyncio.create_task(
                telegram_bot.send_review_reply_notification(
                    review_data, reply.text, "shop"
                )
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reply to shop review: {str(e)}")
