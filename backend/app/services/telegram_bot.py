import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app import models
from app.services.yandex_api import YandexMarketAPI


class TelegramBotService:
    """Service for Telegram bot notifications and interactions"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.application = None
        
        if self.bot_token:
            self.application = Application.builder().token(self.bot_token).build()
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [InlineKeyboardButton("📊 Today's Stats", callback_data="stats_today")],
            [InlineKeyboardButton("📈 This Week", callback_data="stats_week")],
            [InlineKeyboardButton("📅 This Month", callback_data="stats_month")],
            [InlineKeyboardButton("🔄 Sync Now", callback_data="sync_now")],
            [InlineKeyboardButton("⚡ Force Sync", callback_data="force_sync")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 Yandex Market Manager Bot\n\n"
            "Choose an option:",
            reply_markup=reply_markup
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        await self._show_period_selection(update)
    
    async def _show_period_selection(self, update: Update):
        """Show period selection keyboard"""
        keyboard = [
            [InlineKeyboardButton("📊 Today", callback_data="stats_today")],
            [InlineKeyboardButton("📈 This Week", callback_data="stats_week")],
            [InlineKeyboardButton("📅 This Month", callback_data="stats_month")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "Select period for statistics:"
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("stats_"):
            period = query.data.split("_")[1]
            stats_text = await self._get_stats_for_period(period)
            
            keyboard = [
                [InlineKeyboardButton("📊 Today", callback_data="stats_today")],
                [InlineKeyboardButton("📈 This Week", callback_data="stats_week")],
                [InlineKeyboardButton("📅 This Month", callback_data="stats_month")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')
        
        elif query.data == "back_to_menu":
            keyboard = [
                [InlineKeyboardButton("📊 Today's Stats", callback_data="stats_today")],
                [InlineKeyboardButton("📈 This Week", callback_data="stats_week")],
                [InlineKeyboardButton("📅 This Month", callback_data="stats_month")],
                [InlineKeyboardButton("🔄 Sync Now", callback_data="sync_now")],
                [InlineKeyboardButton("⚡ Force Sync", callback_data="force_sync")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🤖 Yandex Market Manager Bot\n\nChoose an option:",
                reply_markup=reply_markup
            )
        
        elif query.data in ["sync_now", "force_sync"]:
            force = query.data == "force_sync"
            await query.edit_message_text("🔄 Syncing... Please wait.")
            result = await self._sync_all(force)
            await query.edit_message_text(result)
    
    async def _get_stats_for_period(self, period: str) -> str:
        """Get statistics for a specific period"""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_stats_sync, period)
    
    def _get_stats_sync(self, period: str) -> str:
        """Synchronous version of get_stats_for_period"""
        db = SessionLocal()
        try:
            # Calculate date range
            now = datetime.utcnow()
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_name = "Today"
            elif period == "week":
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                period_name = "This Week"
            elif period == "month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                period_name = "This Month"
            else:
                start_date = now - timedelta(days=365)
                period_name = "All Time"
            
            # Get orders for period
            orders = db.query(models.Order).filter(
                models.Order.created_at >= start_date,
                models.Order.status == models.OrderStatus.COMPLETED
            ).all()
            
            # Calculate statistics
            total_orders = len(orders)
            total_revenue = sum(order.total_amount for order in orders)
            total_profit = sum(order.get_profit(db) for order in orders)
            total_cost = total_revenue - total_profit
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Get top products
            from sqlalchemy import func
            top_products = (
                db.query(
                    models.Product.id,
                    models.Product.name,
                    func.count(models.Order.id).label("total_sales"),
                    func.sum(models.Order.total_amount).label("total_revenue")
                )
                .join(models.Order)
                .filter(
                    models.Order.created_at >= start_date,
                    models.Order.status == models.OrderStatus.COMPLETED
                )
                .group_by(models.Product.id, models.Product.name)
                .order_by(func.count(models.Order.id).desc())
                .limit(5)
                .all()
            )
            
            # Build message
            message = f"<b>📊 Statistics - {period_name}</b>\n\n"
            message += f"💰 <b>Revenue:</b> ₽{total_revenue:,.2f}\n"
            message += f"💵 <b>Profit:</b> ₽{total_profit:,.2f}\n"
            message += f"📦 <b>Cost:</b> ₽{total_cost:,.2f}\n"
            message += f"📈 <b>Profit Margin:</b> {profit_margin:.1f}%\n"
            message += f"🛒 <b>Total Orders:</b> {total_orders}\n\n"
            
            if top_products:
                message += "<b>🏆 Top Products:</b>\n"
                for idx, product in enumerate(top_products, 1):
                    message += f"{idx}. {product.name}\n"
                    message += f"   Sales: {product.total_sales} | Revenue: ₽{float(product.total_revenue or 0):,.2f}\n"
            
            return message
            
        finally:
            db.close()
    
    async def _sync_all(self, force: bool = False) -> str:
        """Sync all data from Yandex Market"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_all_sync, force)
    
    def _sync_all_sync(self, force: bool = False) -> str:
        """Synchronous version of sync_all"""
        try:
            from app.routers.sync import sync_products, sync_orders
            from app.database import SessionLocal
            
            db = SessionLocal()
            try:
                # Sync products
                products_result = sync_products(force=force, db=db)
                
                # Sync orders
                orders_result = sync_orders(db=db)
                
                message = "✅ <b>Sync Complete</b>\n\n"
                message += f"📦 Products: {products_result.products_synced} synced\n"
                message += f"   - Created: {products_result.products_created}\n"
                message += f"   - Updated: {products_result.products_updated}\n"
                message += f"🛒 Orders: {orders_result.get('orders_created', 0)} created\n"
                
                if products_result.errors:
                    message += f"\n⚠️ Errors: {len(products_result.errors)}"
                
                return message
            finally:
                db.close()
        except Exception as e:
            return f"❌ Sync failed: {str(e)}"
    
    def send_order_notification_sync(self, order: models.Order, event_type: str = "created"):
        """Send order notification to Telegram (sync version)"""
        if not self.chat_id:
            return
        
        db = SessionLocal()
        try:
            product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
            
            if event_type == "created":
                emoji = "🆕"
                title = "New Order"
            elif event_type == "status_changed":
                emoji = "🔄"
                title = "Order Status Changed"
            elif event_type == "completed":
                emoji = "✅"
                title = "Order Completed"
            else:
                emoji = "📦"
                title = "Order Update"
            
            message = f"{emoji} <b>{title}</b>\n\n"
            message += f"🆔 <b>Order ID:</b> {order.yandex_order_id}\n"
            if product:
                message += f"📦 <b>Product:</b> {product.name}\n"
            message += f"💰 <b>Amount:</b> ₽{order.total_amount:,.2f}\n"
            message += f"📊 <b>Status:</b> {order.status.value}\n"
            if order.customer_name:
                message += f"👤 <b>Customer:</b> {order.customer_name}\n"
            
            if event_type == "completed" and product:
                profit = order.get_profit(db)
                message += f"💵 <b>Profit:</b> ₽{profit:,.2f}\n"
            
            # Send message asynchronously
            asyncio.create_task(self._send_message(message))
        finally:
            db.close()
    
    async def _send_message(self, text: str, parse_mode: str = 'HTML'):
        """Send message to configured chat"""
        if not self.application or not self.chat_id:
            return
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
        except Exception as e:
            print(f"Failed to send Telegram message: {str(e)}")
    
    async def send_review_notification(self, review: Dict, review_type: str = "product"):
        """Send notification when a new review is received"""
        if not self.chat_id:
            return
        
        rating = review.get("rating", 0)
        rating_emoji = "⭐" * int(rating) if rating else "❓"
        author = review.get("author", {}).get("name", "Anonymous")
        text = review.get("text", "")
        product_name = review.get("product", {}).get("name", "Unknown Product") if review_type == "product" else None
        
        message = f"💬 <b>New {review_type.capitalize()} Review</b>\n\n"
        if product_name:
            message += f"📦 <b>Product:</b> {product_name}\n"
        message += f"{rating_emoji} <b>Rating:</b> {rating}/5\n"
        message += f"👤 <b>Author:</b> {author}\n"
        if text:
            message += f"\n💭 <b>Review:</b>\n{text[:500]}{'...' if len(text) > 500 else ''}\n"
        
        await self._send_message(message)
    
    async def send_review_reply_notification(self, review: Dict, reply_text: str, review_type: str = "product"):
        """Send notification when replying to a review"""
        if not self.chat_id:
            return
        
        rating = review.get("rating", 0)
        rating_emoji = "⭐" * int(rating) if rating else "❓"
        author = review.get("author", {}).get("name", "Anonymous")
        review_text = review.get("text", "")
        product_name = review.get("product", {}).get("name", "Unknown Product") if review_type == "product" else None
        
        message = f"💬 <b>Replied to {review_type.capitalize()} Review</b>\n\n"
        if product_name:
            message += f"📦 <b>Product:</b> {product_name}\n"
        message += f"{rating_emoji} <b>Rating:</b> {rating}/5\n"
        message += f"👤 <b>Customer:</b> {author}\n"
        if review_text:
            message += f"\n💭 <b>Customer Review:</b>\n{review_text[:300]}{'...' if len(review_text) > 300 else ''}\n"
        message += f"\n✍️ <b>Your Reply:</b>\n{reply_text[:500]}{'...' if len(reply_text) > 500 else ''}\n"
        
        await self._send_message(message)
    
    async def send_chat_message_notification(self, order: models.Order, customer_message: Optional[str], reply_text: str):
        """Send notification when replying to a customer chat message"""
        if not self.chat_id:
            return
        
        db = SessionLocal()
        try:
            product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
            
            message = f"💬 <b>Chat Message Reply</b>\n\n"
            message += f"🆔 <b>Order ID:</b> {order.yandex_order_id}\n"
            if product:
                message += f"📦 <b>Product:</b> {product.name}\n"
            if order.customer_name:
                message += f"👤 <b>Customer:</b> {order.customer_name}\n"
            
            if customer_message:
                message += f"\n💭 <b>Customer Message:</b>\n{customer_message[:300]}{'...' if len(customer_message) > 300 else ''}\n"
            
            message += f"\n✍️ <b>Your Reply:</b>\n{reply_text[:500]}{'...' if len(reply_text) > 500 else ''}\n"
            
            await self._send_message(message)
        finally:
            db.close()
    
    async def start_polling(self):
        """Start the bot polling"""
        if self.application:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
    
    async def stop_polling(self):
        """Stop the bot polling"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


# Global bot instance
telegram_bot = TelegramBotService()
