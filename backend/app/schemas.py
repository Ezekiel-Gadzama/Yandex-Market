from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from app.models import ProductType, OrderStatus


# Product Schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    product_type: ProductType = ProductType.DIGITAL
    cost_price: float = Field(gt=0, description="Cost to buy from supplier")
    selling_price: float = Field(gt=0, description="Price on Yandex Market")
    supplier_url: Optional[str] = None
    supplier_name: Optional[str] = None
    yandex_market_id: Optional[str] = None
    yandex_market_sku: Optional[str] = None
    email_template_id: Optional[int] = None
    is_active: bool = True
    
    # Yandex Market product details
    yandex_model: Optional[str] = "DBS"  # Model type (DBS for digital products)
    yandex_category_id: Optional[str] = None
    yandex_category_path: Optional[str] = None
    yandex_brand: Optional[str] = None
    yandex_platform: Optional[str] = None
    yandex_localization: Optional[str] = None
    yandex_publication_type: Optional[str] = None
    yandex_activation_territory: Optional[str] = "all countries"
    yandex_edition: Optional[str] = None
    yandex_series: Optional[str] = None
    yandex_age_restriction: Optional[str] = None
    yandex_activation_instructions: Optional[bool] = True
    
    # Pricing and discounts
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = 0
    
    # Media (JSON arrays as strings)
    yandex_images: Optional[List[str]] = None
    yandex_videos: Optional[List[str]] = None
    
    # Inventory/Stock Management
    stock_quantity: Optional[int] = None
    warehouse_id: Optional[int] = None
    
    # Inventory/Stock Management (for FBS model)
    stock_quantity: Optional[int] = 0
    warehouse_id: Optional[int] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    product_type: Optional[ProductType] = None
    cost_price: Optional[float] = Field(None, gt=0)
    selling_price: Optional[float] = Field(None, gt=0)
    supplier_url: Optional[str] = None
    supplier_name: Optional[str] = None
    email_template_id: Optional[int] = None
    is_active: Optional[bool] = None
    
    # Yandex Market product details
    yandex_model: Optional[str] = None
    yandex_category_id: Optional[str] = None
    yandex_category_path: Optional[str] = None
    yandex_brand: Optional[str] = None
    yandex_platform: Optional[str] = None
    yandex_localization: Optional[str] = None
    yandex_publication_type: Optional[str] = None
    yandex_activation_territory: Optional[str] = None
    yandex_edition: Optional[str] = None
    yandex_series: Optional[str] = None
    yandex_age_restriction: Optional[str] = None
    yandex_activation_instructions: Optional[bool] = None
    
    # Pricing and discounts
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    
    # Media
    yandex_images: Optional[List[str]] = None
    yandex_videos: Optional[List[str]] = None
    
    # Inventory/Stock Management
    stock_quantity: Optional[int] = None
    warehouse_id: Optional[int] = None


class Product(ProductBase):
    id: int
    profit: float
    profit_percentage: float
    is_synced: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Email Template Schemas
class EmailTemplateBase(BaseModel):
    name: str
    subject: str
    body: str


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class EmailTemplate(EmailTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Activation Key Schemas
class ActivationKeyBase(BaseModel):
    key: str
    product_id: int


class ActivationKeyCreate(ActivationKeyBase):
    pass


class ActivationKey(ActivationKeyBase):
    id: int
    is_used: bool
    used_at: Optional[datetime] = None
    order_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Order Schemas
class OrderBase(BaseModel):
    yandex_order_id: str
    product_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    quantity: int = 1
    total_amount: float


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    activation_code_sent: Optional[bool] = None
    activation_key_id: Optional[int] = None


class Order(OrderBase):
    id: int
    status: OrderStatus
    activation_code_sent: bool
    activation_code_sent_at: Optional[datetime] = None
    profit: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Dashboard Schemas
class DashboardStats(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    pending_orders: int
    completed_orders: int
    total_revenue: float
    total_profit: float
    total_cost: float
    profit_margin: float


class TopProduct(BaseModel):
    product_id: int
    product_name: str
    total_sales: int
    total_revenue: float
    total_profit: float


class DashboardData(BaseModel):
    stats: DashboardStats
    top_products: List[TopProduct]
    recent_orders: List[Order]


# Sync Schema
class SyncRequest(BaseModel):
    force: bool = False


class SyncResult(BaseModel):
    success: bool
    products_synced: int
    products_created: int
    products_updated: int
    products_pushed: int = 0  # Number of products pushed to Yandex
    errors: List[str] = []


# Product Template Schemas
class ProductTemplateBase(BaseModel):
    name: str
    template_data: Dict[str, Any]  # All product fields as a dictionary


class ProductTemplateCreate(ProductTemplateBase):
    pass


class ProductTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None


class ProductTemplate(ProductTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @validator('template_data', pre=True)
    def parse_template_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v
    
    class Config:
        from_attributes = True


# Product Variant Schemas
class ProductVariantBase(BaseModel):
    variant_name: str  # e.g., "Enhanced Edition•Kazakhstan•PC"
    variant_sku: Optional[str] = None
    edition: Optional[str] = None
    platform: Optional[str] = None
    activation_territory: Optional[str] = None
    localization: Optional[str] = None
    selling_price: float = Field(gt=0)
    original_price: Optional[float] = None
    cost_price: float = Field(gt=0)
    is_active: bool = True
    stock_quantity: int = 0


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    variant_name: Optional[str] = None
    variant_sku: Optional[str] = None
    edition: Optional[str] = None
    platform: Optional[str] = None
    activation_territory: Optional[str] = None
    localization: Optional[str] = None
    selling_price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = None
    cost_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    stock_quantity: Optional[int] = None


class ProductVariant(ProductVariantBase):
    id: int
    product_id: int
    yandex_market_id: Optional[str] = None
    yandex_market_sku: Optional[str] = None
    is_synced: bool
    profit: float
    profit_percentage: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
