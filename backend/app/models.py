from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
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
    CANCELLED = "cancelled"
    FAILED = "failed"


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
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
    yandex_market_id = Column(String, unique=True, index=True)  # Product ID on Yandex Market
    yandex_market_sku = Column(String, unique=True, index=True)  # SKU on Yandex Market
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
    
    # Media
    yandex_images = Column(Text)  # JSON array of image URLs
    yandex_videos = Column(Text)  # JSON array of video URLs
    
    # Inventory/Stock Management (for FBS model - not applicable for DBS digital products)
    stock_quantity = Column(Integer, default=0)  # Current stock quantity
    warehouse_id = Column(Integer, nullable=True)  # Warehouse ID if using multiple warehouses
    
    # Email template for activation
    email_template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Note: Relationships removed - use queries instead
    # To get orders: db.query(Order).filter(Order.product_id == self.id).all()
    # To get activation_keys: db.query(ActivationKey).filter(ActivationKey.product_id == self.id).all()
    # To get email_template: db.query(EmailTemplate).filter(EmailTemplate.id == self.email_template_id).first()
    
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
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)  # HTML template with placeholders
    
    # Placeholders: {order_number}, {product_name}, {activation_code}, {expiry_date}, {instructions}
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


class ProductVariant(Base):
    """Product variants/options (e.g., different editions, platforms, territories with different prices)"""
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Variant identification
    variant_name = Column(String, nullable=False)  # e.g., "Enhanced Edition•Kazakhstan•PC"
    variant_sku = Column(String, unique=True, index=True)  # Unique SKU for this variant
    
    # Variant-specific attributes
    edition = Column(String)  # e.g., "Enhanced Edition", "Premium Edition"
    platform = Column(String)  # e.g., "PC", "PlayStation 4, PlayStation 5"
    activation_territory = Column(String)  # e.g., "Kazakhstan", "all countries"
    localization = Column(String)  # e.g., "Russian subtitles and interface"
    
    # Variant pricing
    selling_price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    cost_price = Column(Float, nullable=False)  # Cost for this specific variant
    
    # Variant status
    is_active = Column(Boolean, default=True)
    stock_quantity = Column(Integer, default=0)  # Stock for this variant
    
    # Yandex Market integration
    yandex_market_id = Column(String, unique=True, index=True, nullable=True)
    yandex_market_sku = Column(String, unique=True, index=True, nullable=True)
    is_synced = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Note: Relationships removed - use queries instead
    # To get product: db.query(Product).filter(Product.id == self.product_id).first()
    
    @property
    def profit(self) -> float:
        """Calculate profit per unit for this variant"""
        return self.selling_price - self.cost_price
    
    @property
    def profit_percentage(self) -> float:
        """Calculate profit percentage for this variant"""
        if self.cost_price == 0:
            return 0
        return ((self.selling_price - self.cost_price) / self.cost_price) * 100


class ProductTemplate(Base):
    __tablename__ = "product_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    
    # Store all product fields as JSON
    template_data = Column(Text, nullable=False)  # JSON string containing all product fields
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Note: Relationships removed - use queries instead


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    yandex_order_id = Column(String, unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Customer information
    customer_name = Column(String)
    customer_email = Column(String, index=True)
    customer_phone = Column(String)
    
    # Order details
    quantity = Column(Integer, default=1)
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    # Fulfillment
    activation_code_sent = Column(Boolean, default=False)
    activation_code_sent_at = Column(DateTime(timezone=True), nullable=True)
    activation_key_id = Column(Integer, ForeignKey("activation_keys.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Note: Relationships removed - use queries instead
    # To get product: db.query(Product).filter(Product.id == self.product_id).first()
    # To get activation_key: db.query(ActivationKey).filter(ActivationKey.id == self.activation_key_id).first()
    
    def get_profit(self, db) -> float:
        """Calculate profit for this order (requires db session)"""
        from app import models
        product = db.query(models.Product).filter(models.Product.id == self.product_id).first()
        if product:
            return self.total_amount - (product.cost_price * self.quantity)
        return 0
