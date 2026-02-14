"""
Service to periodically check for new reviews
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Set
from app.database import SessionLocal
from app.services.yandex_api import YandexMarketAPI


class ReviewChecker:
    """Periodically checks for new reviews and sends notifications"""
    
    def __init__(self):
        self.last_checked_reviews: Set[str] = set()  # Store review IDs we've already notified about
        self.last_checked_shop_reviews: Set[str] = set()
    
    async def check_for_new_reviews(self, business_id: int = None):
        """Check for new product and shop reviews
        
        Args:
            business_id: Business ID to check reviews for (required)
        """
        if not business_id:
            print("[Review Checker] Skipping review check: business_id is required")
            return
        
        try:
            yandex_api = YandexMarketAPI(business_id=business_id)
            
            # Check product reviews
            product_reviews = yandex_api.get_product_reviews(limit=50)
            new_product_reviews = [
                r for r in product_reviews 
                if r.get("id") and r.get("id") not in self.last_checked_reviews
            ]
            
            for review in new_product_reviews:
                review_id = review.get("id")
                if review_id:
                    self.last_checked_reviews.add(review_id)
            
            # Check shop reviews
            shop_reviews = yandex_api.get_shop_reviews(limit=50)
            new_shop_reviews = [
                r for r in shop_reviews 
                if r.get("id") and r.get("id") not in self.last_checked_shop_reviews
            ]
            
            for review in new_shop_reviews:
                review_id = review.get("id")
                if review_id:
                    self.last_checked_shop_reviews.add(review_id)
            
            if new_product_reviews or new_shop_reviews:
                print(f"[Review Checker] Found {len(new_product_reviews)} new product reviews and {len(new_shop_reviews)} new shop reviews")
        
        except Exception as e:
            print(f"[Review Checker] Error checking reviews: {str(e)}")
    
    async def start_periodic_check(self, interval_minutes: int = 15, business_id: int = None):
        """Start periodic review checking
        
        Args:
            interval_minutes: Interval between checks in minutes
            business_id: Business ID to check reviews for (required)
        """
        if not business_id:
            print("[Review Checker] Skipping periodic review check: business_id is required")
            return
        
        while True:
            try:
                await self.check_for_new_reviews(business_id=business_id)
            except Exception as e:
                print(f"[Review Checker] Error in periodic check: {str(e)}")
            
            await asyncio.sleep(interval_minutes * 60)


# Global review checker instance
review_checker = ReviewChecker()
