"""Helpers for product cost lookup by date. Used for correct profit calculation on past orders."""
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from app import models


def get_product_cost_at_date(
    db: Session,
    product_id: int,
    order_date: Optional[datetime],
) -> float:
    """
    Return the cost per unit for a product at a given order date.
    Uses ProductCostHistory: finds the period where start_date <= order_date and (end_date is null or end_date >= order_date).
    Falls back to product.cost_price if no matching history.
    """
    if order_date is None:
        order_date_d = date.today()
    else:
        order_date_d = order_date.date() if hasattr(order_date, "date") else order_date

    row = (
        db.query(models.ProductCostHistory)
        .filter(
            models.ProductCostHistory.product_id == product_id,
            models.ProductCostHistory.start_date <= order_date_d,
            (models.ProductCostHistory.end_date.is_(None)) | (models.ProductCostHistory.end_date >= order_date_d),
        )
        .order_by(models.ProductCostHistory.start_date.desc())
        .first()
    )
    if row is not None:
        return float(row.amount)

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is not None:
        return float(product.cost_price or 0)
    return 0.0
