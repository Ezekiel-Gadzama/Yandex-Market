from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.database import engine, Base, SessionLocal
from app.routers import products, orders, dashboard, email_templates, sync, webhooks, reviews, chat, media, product_templates, inventory, product_variants
from app.config import settings
from app.initial_data import create_default_email_template
from app.services.yandex_api import YandexMarketAPI
from app.services.telegram_bot import telegram_bot
from app.services.review_checker import review_checker
from app import models
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Thread pool for running synchronous API calls
executor = ThreadPoolExecutor(max_workers=2)

def _sync_products_sync():
    """Sync products FROM Yandex Market TO local database (one-way sync)"""
    try:
        db = SessionLocal()
        try:
            yandex_api = YandexMarketAPI()
            yandex_products = yandex_api.get_products()
            
            for yandex_product in yandex_products:
                try:
                    yandex_id = yandex_product.get("id")
                    yandex_sku = yandex_product.get("sku")
                    
                    existing_product = db.query(models.Product).filter(
                        (models.Product.yandex_market_id == yandex_id) |
                        (models.Product.yandex_market_sku == yandex_sku)
                    ).first()
                    
                    if existing_product:
                        if not existing_product.is_synced:
                            # Preserve local-only fields
                            preserved_cost_price = existing_product.cost_price
                            preserved_supplier_url = existing_product.supplier_url
                            preserved_supplier_name = existing_product.supplier_name
                            preserved_email_template_id = existing_product.email_template_id
                            
                            # Update with Yandex data (Yandex is source of truth)
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
                    else:
                        # Create new product from Yandex
                        new_product = models.Product(
                            name=yandex_product.get("name", "Unknown Product"),
                            description=yandex_product.get("description"),
                            yandex_market_id=yandex_id,
                            yandex_market_sku=yandex_sku,
                            selling_price=yandex_product.get("price", 0),
                            cost_price=0,
                            is_synced=True,
                            product_type=models.ProductType.DIGITAL
                        )
                        
                        # Set active status from Yandex
                        availability = yandex_product.get("availability", "")
                        if availability:
                            new_product.is_active = (availability == "ACTIVE")
                        
                        db.add(new_product)
                except Exception:
                    continue
            
            db.commit()
            print(f"[Auto-Sync] Products synced from Yandex at {datetime.utcnow()}")
        finally:
            db.close()
    except Exception as e:
        print(f"[Auto-Sync] Error syncing products: {str(e)}")

def _sync_orders_sync():
    """Synchronous order sync function"""
    try:
        db = SessionLocal()
        try:
            yandex_api = YandexMarketAPI()
            yandex_orders = yandex_api.get_orders()
            
            for yandex_order in yandex_orders:
                try:
                    existing_order = db.query(models.Order).filter(
                        models.Order.yandex_order_id == str(yandex_order.get("id"))
                    ).first()
                    
                    if not existing_order:
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
                            
                            # Auto-fulfill digital products
                            if product.product_type == models.ProductType.DIGITAL:
                                from app.services.order_service import OrderService
                                order_service = OrderService(db)
                                order_service.auto_fulfill_order(new_order)
                except Exception:
                    continue
            
            db.commit()
            print(f"[Auto-Sync] Orders synced at {datetime.utcnow()}")
        finally:
            db.close()
    except Exception as e:
        print(f"[Auto-Sync] Error syncing orders: {str(e)}")

async def auto_sync_products():
    """Automatically sync products from Yandex Market (async wrapper)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, _sync_products_sync)

async def auto_sync_orders():
    """Automatically sync orders from Yandex Market (async wrapper)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, _sync_orders_sync)

async def periodic_sync():
    """Periodic sync task - runs every 5 minutes"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        await auto_sync_products()
        await auto_sync_orders()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables automatically: {e}")
    
    # Create default email template
    try:
        create_default_email_template()
    except Exception:
        pass
    
    # Initial sync on startup
    print("[Startup] Performing initial sync from Yandex Market...")
    await auto_sync_products()
    await auto_sync_orders()
    
    # Start periodic sync task
    sync_task = asyncio.create_task(periodic_sync())
    
    # Start review checker task
    review_checker_task = asyncio.create_task(review_checker.start_periodic_check(interval_minutes=15))
    
    # Start Telegram bot if configured
    bot_task = None
    if telegram_bot.application:
        try:
            print("[Startup] Starting Telegram bot...")
            bot_task = asyncio.create_task(telegram_bot.start_polling())
        except Exception as e:
            print(f"[Startup] Warning: Could not start Telegram bot: {e}")
    
    yield
    
    # Shutdown
    sync_task.cancel()
    review_checker_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    try:
        await review_checker_task
    except asyncio.CancelledError:
        pass
    
    # Stop Telegram bot
    if bot_task:
        try:
            await telegram_bot.stop_polling()
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            print(f"[Shutdown] Warning: Error stopping Telegram bot: {e}")

app = FastAPI(
    title="Yandex Market Digital Products Manager",
    description="Complete ecosystem for managing digital products on Yandex Market",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(email_templates.router, prefix="/api/email-templates", tags=["email-templates"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(product_templates.router, prefix="/api/product-templates", tags=["product-templates"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(product_variants.router, prefix="/api", tags=["product-variants"])


@app.get("/")
async def root():
    return {"message": "Yandex Market Digital Products Manager API"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
