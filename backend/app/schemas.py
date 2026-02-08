from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from app.models import ProductType, OrderStatus


# Product Schemas
# Products are only synced from Yandex Market, not created manually
# All Yandex data is stored in yandex_full_data JSON field

class ProductBase(BaseModel):
    """Base product schema - only essential local fields"""
    name: str
    description: Optional[str] = None
    product_type: ProductType = ProductType.DIGITAL
    cost_price: float = Field(ge=0, description="Cost to buy from supplier")
    selling_price: float = Field(ge=0, description="Price on Yandex Market")
    supplier_url: Optional[str] = None
    supplier_name: Optional[str] = None
    yandex_market_id: Optional[str] = None
    yandex_market_sku: Optional[str] = None
    email_template_id: Optional[int] = None
    documentation_id: Optional[int] = None
    is_active: bool = True
    # All Yandex fields are stored in yandex_full_data JSON, not as individual fields


class ProductUpdate(BaseModel):
    """Update product - only local-only fields and dynamic Yandex JSON updates"""
    # Essential local-only fields (not in Yandex)
    cost_price: Optional[float] = Field(None, ge=0)
    supplier_url: Optional[str] = None
    supplier_name: Optional[str] = None
    email_template_id: Optional[int] = None
    documentation_id: Optional[int] = None
    is_active: Optional[bool] = None
    
    # Dynamic field updates from Yandex JSON (all Yandex fields are edited here)
    yandex_field_updates: Optional[Dict[str, Any]] = None


class Product(ProductBase):
    id: int
    profit: float
    profit_percentage: float
    is_synced: bool
    yandex_full_data: Optional[Dict[str, Any]] = None  # Complete Yandex JSON data
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Email Template Schemas
class EmailTemplateBase(BaseModel):
    name: str
    body: str  # Plain text template body
    random_key: bool = True  # If True, activation key is auto-generated
    required_login: bool = False  # If True, adds "Done! the operator..." text
    activate_till_days: int = 30  # Number of days until activation code expires (for Yandex deliverDigitalGoods)


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    body: Optional[str] = None
    random_key: Optional[bool] = None
    required_login: Optional[bool] = None
    activate_till_days: Optional[int] = None


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


class OrderItem(BaseModel):
    """Represents a single product/item in an order"""
    product_id: Optional[int] = None  # None if product not in database
    product_name: str
    quantity: int
    item_price: float  # Price per item
    item_total: float  # Total for this item (item_price * quantity)
    yandex_item_id: Optional[int] = None
    yandex_offer_id: Optional[str] = None
    activation_code_sent: bool = False
    activation_key_id: Optional[int] = None
    email_template_id: Optional[int] = None
    documentation_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class Order(OrderBase):
    id: int
    status: OrderStatus
    yandex_status: Optional[str] = None
    yandex_order_data: Optional[Dict[str, Any]] = None
    activation_code_sent: bool
    activation_code_sent_at: Optional[datetime] = None
    activation_key_id: Optional[int] = None
    profit: float = 0.0
    product_name: Optional[str] = None  # Product name for display (first product)
    items: Optional[List[OrderItem]] = None  # All products/items in this order
    items_count: Optional[int] = None  # Number of products in this order
    delivery_type: Optional[str] = None  # "DIGITAL" or "DELIVERY" from Yandex API
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
    processing_orders: int
    completed_orders: int
    cancelled_orders: int
    finished_orders: int
    successful_orders: int  # completed + finished
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


# App Settings Schemas
class AppSettingsBase(BaseModel):
    processing_time_min: int = Field(ge=1, description="Minimum processing time in minutes")
    processing_time_max: Optional[int] = Field(None, ge=1, description="Maximum processing time in minutes (optional)")
    maximum_wait_time_value: Optional[int] = Field(None, ge=1, description="Maximum wait time value")
    maximum_wait_time_unit: Optional[str] = Field(None, description="Unit: minutes, hours, days, weeks")
    working_hours_text: Optional[str] = None
    company_email: Optional[str] = None
    
    # Yandex Market Business API - optional overrides for .env
    yandex_api_token: Optional[str] = None
    yandex_business_id: Optional[str] = None  # Primary identifier for Business API
    yandex_campaign_id: Optional[str] = None  # Legacy support
    yandex_api_url: str = Field(default="https://api.partner.market.yandex.ru")
    
    # SMTP - optional overrides for .env
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    
    # Security
    secret_key: Optional[str] = None
    
    
    # Order Activation Settings
    auto_activation_enabled: bool = False  # If True, automatically send activation when order comes in


class AppSettingsUpdate(BaseModel):
    processing_time_min: Optional[int] = Field(None, ge=1)
    processing_time_max: Optional[int] = Field(None, ge=1)
    maximum_wait_time_value: Optional[int] = Field(None, ge=1)
    maximum_wait_time_unit: Optional[str] = None
    working_hours_text: Optional[str] = None
    company_email: Optional[str] = None
    yandex_api_token: Optional[str] = None
    yandex_business_id: Optional[str] = None
    yandex_campaign_id: Optional[str] = None
    yandex_client_secret: Optional[str] = None
    yandex_api_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    secret_key: Optional[str] = None
    auto_activation_enabled: Optional[bool] = None


class AppSettings(AppSettingsBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Client Schemas
class ClientBase(BaseModel):
    name: str
    email: EmailStr

class ClientCreate(ClientBase):
    purchased_product_ids: Optional[List[int]] = []

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    purchased_product_ids: Optional[List[int]] = None

class Client(ClientBase):
    id: int
    purchased_product_ids: List[int] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Marketing Email Template Schemas
class MarketingEmailTemplateBase(BaseModel):
    name: str
    subject: str
    body: str  # Rich text body with HTML formatting

class MarketingEmailTemplateCreate(MarketingEmailTemplateBase):
    pass

class MarketingEmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None  # Unified attachments: [{"url": "...", "type": "image|video|file", "name": "..."}, ...]

class MarketingEmailTemplate(MarketingEmailTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Documentation Schemas
class DocumentationBase(BaseModel):
    name: str
    description: Optional[str] = Field(None, max_length=120, description="Description with a maximum of 120 characters")
    file_url: Optional[str] = None
    link_url: Optional[str] = None
    content: Optional[str] = None  # Rich text content (HTML)
    type: str = 'file'  # 'file', 'link', or 'text'


class DocumentationCreate(DocumentationBase):
    pass


class DocumentationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = Field(None, max_length=120, description="Description with a maximum of 120 characters")
    file_url: Optional[str] = None
    link_url: Optional[str] = None
    content: Optional[str] = None
    type: Optional[str] = None


class Documentation(DocumentationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Product Analytics Schemas
class ProductAnalytics(BaseModel):
    product_id: int
    product_name: str
    total_orders: int
    completed_orders: int
    total_revenue: float
    total_profit: float
    profit_margin: float
    average_order_value: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    class Config:
        from_attributes = True
