from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class ProductType(str, enum.Enum):
    DIGITAL = "digital"
    PHYSICAL = "physical"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FINISHED = "finished"  # Marked as finished after completing buyer interaction
    CANCELLED = "cancelled"
    FAILED = "failed"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        # Composite unique constraints: unique per business, not globally
        UniqueConstraint('business_id', 'yandex_market_id', name='uq_product_business_yandex_id'),
        UniqueConstraint('business_id', 'yandex_market_sku', name='uq_product_business_yandex_sku'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - links product to admin's business
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    product_type = Column(SQLEnum(ProductType), default=ProductType.DIGITAL, nullable=False)
    
    # Pricing
    cost_price = Column(Float, nullable=False)  # Cost to buy from supplier
    selling_price = Column(Float, nullable=False)  # Price on Yandex Market
    
    # Supplier information
    supplier_url = Column(String)  # Link to original website
    supplier_name = Column(String)
    
    # Yandex Market integration
    yandex_market_id = Column(String, index=True)  # Product ID on Yandex Market (unique per business)
    yandex_market_sku = Column(String, index=True)  # SKU on Yandex Market (unique per business)
    is_synced = Column(Boolean, default=False)  # Whether synced with Yandex Market
    
    # Yandex Market product details
    yandex_model = Column(String, default="DBS")  # Model type (DBS for digital products)
    yandex_category_id = Column(String)  # Yandex Market category ID
    yandex_category_path = Column(String)  # Category path (e.g., "Electronics > Gaming > Games")
    yandex_brand = Column(String)  # Brand name (e.g., "Sony")
    yandex_platform = Column(String)  # Platform (e.g., "PlayStation 4, PlayStation 5")
    yandex_localization = Column(String)  # Localization (e.g., "Russian subtitles")
    yandex_publication_type = Column(String)  # Type of publication (e.g., "complete")
    yandex_activation_territory = Column(String, default="all countries")  # Activation territory
    yandex_edition = Column(String)  # Edition (e.g., "The Trilogy")
    yandex_series = Column(String)  # Game series (e.g., "PlayStation")
    yandex_age_restriction = Column(String)  # Age restriction (e.g., "18+")
    yandex_activation_instructions = Column(Boolean, default=True)  # Has activation instructions
    
    # Pricing and discounts
    original_price = Column(Float)  # Original price before discount
    discount_percentage = Column(Float, default=0)  # Discount percentage
    
    # Physical product details
    barcode = Column(String)  # Product barcode (EAN, UPC, etc.)
    width_cm = Column(Float)  # Width in cm
    height_cm = Column(Float)  # Height in cm
    length_cm = Column(Float)  # Length/depth in cm
    weight_kg = Column(Float)  # Weight in kg
    
    # Tax and pricing
    vat_rate = Column(String, default="NOT_APPLICABLE")  # VAT: NOT_APPLICABLE, VAT_0, VAT_10, VAT_20
    crossed_out_price = Column(Float)  # Original price (for showing discounts)
    
    # Certificate-specific fields (for digital gift certificates)
    certificate_type = Column(String)  # Type of certificate
    delivery_type = Column(String)  # Type of delivery
    monetary_certificate_type = Column(String)  # Type of monetary certificate
    certificate_theme = Column(String)  # Theme/design of certificate
    certificate_design = Column(String)  # Design details
    
    # Inventory/Stock Management (for FBS model - not applicable for DBS digital products)
    stock_quantity = Column(Integer, default=0)  # Current stock quantity
    warehouse_id = Column(Integer, nullable=True)  # Warehouse ID if using multiple warehouses
    
    # Email template for activation
    email_template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    
    # Documentation for order fulfillment
    documentation_id = Column(Integer, ForeignKey("documentations.id"), nullable=True)
    
    # Yandex purchase link (optional)
    yandex_purchase_link = Column(String, nullable=True)  # Link to purchase product on Yandex Market
    
    # Usage period for physical products (optional, in days)
    # Used instead of activation template expiry period for physical products
    usage_period = Column(Integer, nullable=True)  # Number of days the product can be used
    
    # Product status
    is_active = Column(Boolean, default=True)  # Whether the product is active/available
    
    # Activation Keys Tracking
    generated_keys = Column(JSONB, default=list)  # List of {key, timestamp, order_id} objects
    
    # Full Yandex Market data (complete JSON from API)
    yandex_full_data = Column(JSONB, nullable=True)  # Complete product data from Yandex Market API
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @property
    def profit(self) -> float:
        """Calculate profit per unit"""
        return self.selling_price - self.cost_price
    
    @property
    def profit_percentage(self) -> float:
        """Calculate profit percentage"""
        if self.cost_price == 0:
            return 0
        return ((self.selling_price - self.cost_price) / self.cost_price) * 100


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - links template to admin's business
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    body = Column(Text, nullable=False)  # Plain text template body (with formatting stored as text)
    random_key = Column(Boolean, default=True)  # If True, activation key is auto-generated
    required_login = Column(Boolean, default=False)  # If True, adds "Done! the operator..." text
    activate_till_days = Column(Integer, default=30)  # Number of days until activation code expires (for Yandex deliverDigitalGoods)
    
    # Unified media attachments (URLs only - Yandex API doesn't support file uploads)
    # Format: [{"url": "...", "type": "image|video|file", "name": "..."}, ...]
    attachments = Column(JSONB, default=list)  # List of attachment objects with url, type, and name
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Note: Relationships removed - use queries instead
    # To get products: db.query(Product).filter(Product.email_template_id == self.id).all()


class ActivationKey(Base):
    __tablename__ = "activation_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    key = Column(String, unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Note: Relationships removed - use queries instead
    # To get product: db.query(Product).filter(Product.id == self.product_id).first()
    # To get order: db.query(Order).filter(Order.activation_key_id == self.id).first()


class AppSettings(Base):
    """Application settings (one per business)"""
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - each business has its own settings
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Processing time
    processing_time_min = Column(Integer, default=20)  # Minimum processing time in minutes
    processing_time_max = Column(Integer, nullable=True)  # Maximum processing time in minutes (optional)
    maximum_wait_time_value = Column(Integer, nullable=True)  # Maximum wait time numeric value
    maximum_wait_time_unit = Column(String, nullable=True)  # Unit: 'minutes', 'hours', 'days', 'weeks'
    
    # Working hours
    working_hours_text = Column(Text, nullable=True)
    
    # Company email
    company_email = Column(String, nullable=True)
    
    # Yandex Market Business API - override .env if set
    yandex_api_token = Column(String, nullable=True)
    yandex_business_id = Column(String, nullable=True)  # Business ID (primary)
    yandex_campaign_id = Column(String, nullable=True)  # Campaign ID (legacy)
    yandex_api_url = Column(String, default="https://api.partner.market.yandex.ru")
    
    # SMTP Configuration - required per business (no .env fallback)
    smtp_host = Column(String, nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_user = Column(String, nullable=True)  # Added missing smtp_user field
    smtp_password = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    
    # Security
    secret_key = Column(String, nullable=True)
    
    # Order Activation Settings
    auto_activation_enabled = Column(Boolean, default=False)  # If True, automatically send activation when order comes in
    
    # Client Management Settings
    auto_append_clients = Column(Boolean, default=False)  # If True, automatically append client orders when customer name matches
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())




class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # Composite unique constraint: one Order record per (yandex_order_id, product_id) combination
        # This allows multiple Order records for the same Yandex order (one per product/item)
        UniqueConstraint('yandex_order_id', 'product_id', name='uq_order_yandex_product'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - links order to admin's business
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    yandex_order_id = Column(String, nullable=False, index=True)  # Removed unique=True - can have multiple orders per Yandex order
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Customer information
    customer_name = Column(String)
    customer_email = Column(String, index=True)
    customer_phone = Column(String)
    buyer_id = Column(String, index=True, nullable=True)  # Yandex buyer ID for tracking same client across orders
    
    # Order details
    quantity = Column(Integer, default=1)
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    yandex_status = Column(String, nullable=True)  # Raw Yandex order status
    
    # Full Yandex order data (includes items with IDs needed for digital goods delivery)
    yandex_order_data = Column(JSONB, nullable=True)
    
    # Fulfillment
    activation_code_sent = Column(Boolean, default=False)
    activation_code_sent_at = Column(DateTime(timezone=True), nullable=True)
    activation_key_id = Column(Integer, ForeignKey("activation_keys.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    order_created_at = Column(DateTime(timezone=True), nullable=True)  # Actual order creation date from Yandex API (creationDate)
    
    # Note: Relationships removed - use queries instead
    # To get product: db.query(Product).filter(Product.id == self.product_id).first()
    # To get activation_key: db.query(ActivationKey).filter(ActivationKey.id == self.activation_key_id).first()
    
    @property
    def profit(self) -> float:
        """Calculate profit for this order.
        
        Uses the SQLAlchemy session bound to the object (if available) to look up
        the product's cost_price. Returns 0.0 if product can't be found.
        """
        try:
            from sqlalchemy import inspect
            session = inspect(self).session
            if session:
                from app import models
                product = session.query(models.Product).filter(models.Product.id == self.product_id).first()
                if product:
                    return self.total_amount - (product.cost_price * self.quantity)
        except Exception:
            pass
        return 0.0


# Association table for client-product many-to-many relationship with purchase tracking
client_products = Table(
    'client_products',
    Base.metadata,
    Column('client_id', Integer, ForeignKey('clients.id', ondelete='CASCADE'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
    Column('quantity', Integer, default=1),  # How many times this product was purchased
    Column('first_purchase_date', DateTime(timezone=True), server_default=func.now()),
    Column('last_purchase_date', DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    # Store all purchase dates for this product (JSON array of datetime strings)
    # Used to track history for -1 button functionality
    Column('purchase_dates_history', JSONB, default=list)  # List of purchase date strings
)


class Client(Base):
    """Clients for marketing email campaigns"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - links client to admin's business
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    buyer_id = Column(String, unique=True, index=True, nullable=True)  # Yandex buyer ID for tracking same client across orders
    
    # List of order IDs associated with this client
    order_ids = Column(JSONB, default=list)  # List of yandex_order_id strings
    
    # Relationship with products (purchase history)
    purchased_products = relationship(
        "Product",
        secondary=client_products,
        backref="clients_who_purchased"
    )
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MarketingEmailTemplate(Base):
    """Email templates for marketing campaigns"""
    __tablename__ = "marketing_email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - links template to admin's business
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)  # Rich text body with HTML formatting
    
    # Unified media attachments
    # Format: [{"url": "...", "type": "image|video|file", "name": "..."}, ...]
    attachments = Column(JSONB, default=list)  # List of attachment objects with url, type, and name
    
    # Frequency and auto-broadcast settings
    frequency_days = Column(Integer, nullable=True)  # Frequency in days for auto-broadcast
    auto_broadcast_enabled = Column(Boolean, default=False)  # If True, automatically broadcast based on frequency
    
    # Default template flag (pinned at top, cannot be deleted or duplicated)
    is_default = Column(Boolean, default=False)  # If True, this is the default template for unique client emails
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatReadStatus(Base):
    """Track when chat messages were last viewed for each order"""
    __tablename__ = "chat_read_status"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, nullable=False, unique=True, index=True)  # yandex_order_id
    last_viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_id = Column(String, nullable=True)  # Last message ID that was viewed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Documentation(Base):
    __tablename__ = "documentations"
    
    id = Column(Integer, primary_key=True, index=True)
    # Business isolation - links documentation to admin's business
    business_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)  # Optional description
    
    # Documentation can be file upload, link, or rich text content
    file_url = Column(String, nullable=True)  # URL to uploaded file
    link_url = Column(String, nullable=True)  # External link URL
    content = Column(Text, nullable=True)  # Rich text content (HTML)
    
    # Type: 'file', 'link', or 'text'
    type = Column(String, nullable=False, default='file')  # 'file', 'link', or 'text'
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    """User accounts for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    
    # User role: 'admin' or 'staff'
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Foreign key to admin who created this staff account (null for admin)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Password reset token (for password reset flow)
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Permissions/Rights (stored as JSONB for flexibility)
    # Each permission is a boolean flag
    permissions = Column(JSONB, default=dict)  # {
    #   "view_staff": bool,  # View and manage staff page
    #   "view_settings": bool,  # View settings page
    #   "client_right": bool,  # Includes: delete_client, edit_client, subtract_client_order, add_client (from clients page)
    #   "view_marketing_emails": bool,  # View marketing emails page
    #   "dashboard_right": bool,  # Includes: view revenue, profit margin, top products charts, revenue/profit in top selling products
    #   "view_product_prices": bool  # Default: True (checked by default)
    # }
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to admin who created this user
    created_by = relationship("User", remote_side=[id], backref="staff_members")
