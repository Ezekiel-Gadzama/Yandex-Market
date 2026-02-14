from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app import models
from app.services.yandex_api import YandexMarketAPI


class OrderService:
    """Service for handling order fulfillment"""
    
    def __init__(self, db: Session):
        self.db = db
        self.yandex_api = YandexMarketAPI()
    
    def _check_all_products_have_templates(self, yandex_order_id: str) -> tuple[bool, list]:
        """Check if all digital products in an order have activation templates
        
        Returns:
            (all_have_templates: bool, missing_templates: list of product names)
        """
        # Get all orders with this yandex_order_id
        all_orders = self.db.query(models.Order).filter(
            models.Order.yandex_order_id == yandex_order_id
        ).all()
        
        missing_templates = []
        for order_record in all_orders:
            product = self.db.query(models.Product).filter(models.Product.id == order_record.product_id).first()
            if product and product.product_type == models.ProductType.DIGITAL:
                if not product.email_template_id:
                    missing_templates.append(product.name)
        
        return len(missing_templates) == 0, missing_templates
    
    def _check_all_digital_products_fulfilled(self, yandex_order_id: str) -> bool:
        """Check if all digital products in an order have been fulfilled (have activation keys)
        
        Returns:
            True if all digital products have activation keys assigned
        """
        # Get all orders with this yandex_order_id
        all_orders = self.db.query(models.Order).filter(
            models.Order.yandex_order_id == yandex_order_id
        ).all()
        
        for order_record in all_orders:
            product = self.db.query(models.Product).filter(models.Product.id == order_record.product_id).first()
            if product and product.product_type == models.ProductType.DIGITAL:
                # Digital product must have activation key assigned
                if not order_record.activation_key_id:
                    return False
        
        return True
    
    def _check_all_products_have_random_key(self, yandex_order_id: str) -> tuple[bool, list]:
        """Check if all digital products in an order have activation templates with random_key = True
        
        Returns:
            (all_have_random_key: bool, products_with_manual_key: list of product names)
        """
        # Get all orders with this yandex_order_id
        all_orders = self.db.query(models.Order).filter(
            models.Order.yandex_order_id == yandex_order_id
        ).all()
        
        products_with_manual_key = []
        for order_record in all_orders:
            product = self.db.query(models.Product).filter(models.Product.id == order_record.product_id).first()
            if product and product.product_type == models.ProductType.DIGITAL:
                if not product.email_template_id:
                    # No template means we can't auto-send (needs manual)
                    products_with_manual_key.append(product.name)
                    continue
                
                # Get the email template
                email_template = self.db.query(models.EmailTemplate).filter(
                    models.EmailTemplate.id == product.email_template_id
                ).first()
                
                if not email_template:
                    # Template not found, skip
                    products_with_manual_key.append(product.name)
                    continue
                
                # Check if random_key is False (manual key required)
                if not email_template.random_key:
                    products_with_manual_key.append(product.name)
        
        return len(products_with_manual_key) == 0, products_with_manual_key
    
    def auto_fulfill_order(self, order: models.Order) -> dict:
        """Automatically fulfill order for digital products
        
        If auto_activation_enabled is True in settings, will also complete the order
        by sending activation code to Yandex Market automatically.
        Only auto-completes if ALL digital products in the order have activation templates.
        """
        # Get product using query
        product = self.db.query(models.Product).filter(models.Product.id == order.product_id).first()
        if not product:
            return {"success": False, "message": "Product not found"}
        
        if product.product_type != models.ProductType.DIGITAL:
            return {"success": False, "message": "Only digital products can be auto-fulfilled"}
        
        # Get an unused activation key
        activation_key = self.db.query(models.ActivationKey).filter(
            models.ActivationKey.product_id == order.product_id,
            models.ActivationKey.is_used == False
        ).first()
        
        if not activation_key:
            # Generate a new key if none available
            import secrets
            import json
            key = f"{product.yandex_market_sku or product.id}-{secrets.token_urlsafe(16)}"
            activation_key = models.ActivationKey(
                product_id=order.product_id,
                key=key
            )
            self.db.add(activation_key)
            self.db.flush()
            
            # Add to product.generated_keys
            existing_keys = []
            if product.generated_keys:
                try:
                    existing_keys = json.loads(product.generated_keys) if isinstance(product.generated_keys, str) else product.generated_keys
                except:
                    existing_keys = []
            
            existing_keys.append({
                "key": key,
                "timestamp": datetime.utcnow().isoformat(),
                "order_id": order.id
            })
            product.generated_keys = json.dumps(existing_keys)
        
        # Assign key to order
        order.activation_key_id = activation_key.id
        activation_key.is_used = True
        activation_key.used_at = datetime.utcnow()
        
        # Update the key's order_id in product.generated_keys
        if product.generated_keys:
            try:
                existing_keys = json.loads(product.generated_keys) if isinstance(product.generated_keys, str) else product.generated_keys
                for key_entry in existing_keys:
                    if key_entry.get('key') == activation_key.key:
                        key_entry['order_id'] = order.id
                        break
                product.generated_keys = json.dumps(existing_keys)
            except:
                pass
        
        # Update order status
        order.status = models.OrderStatus.PROCESSING
        
        self.db.commit()
        
        # Check if auto-activation is enabled
        app_settings = self.db.query(models.AppSettings).first()
        if app_settings and app_settings.auto_activation_enabled:
            # Check if ALL digital products in this order have activation templates
            all_have_templates, missing_templates = self._check_all_products_have_templates(order.yandex_order_id)
            
            if all_have_templates:
                # Check if all products have random_key = True (auto-generated keys)
                # Skip auto-sending if any product requires manual activation keys
                all_have_random_key, products_with_manual_key = self._check_all_products_have_random_key(order.yandex_order_id)
                
                if not all_have_random_key:
                    print(f"ℹ️  Auto-activation skipped for order {order.yandex_order_id}: Requires manual activation keys for: {', '.join(products_with_manual_key)}")
                elif all_have_random_key:
                    # Also check if all digital products have been fulfilled (have activation keys)
                    all_fulfilled = self._check_all_digital_products_fulfilled(order.yandex_order_id)
                    
                    if all_fulfilled:
                        # Get all orders with this yandex_order_id to complete all items
                        all_orders = self.db.query(models.Order).filter(
                            models.Order.yandex_order_id == order.yandex_order_id
                        ).all()
                        
                        # Check if order is already completed to avoid duplicate completion attempts
                        already_completed = any(
                            o.activation_code_sent for o in all_orders
                        )
                        
                        if not already_completed:
                            # Automatically complete the order by sending activation to Yandex for all items
                            try:
                                complete_result = self.complete_order_with_all_items(all_orders)
                                if complete_result.get("success"):
                                    return {
                                        "success": True,
                                        "message": "Order fulfilled and activation sent automatically",
                                        "activation_key": activation_key.key,
                                        "auto_completed": True
                                    }
                            except Exception as e:
                                print(f"⚠️  Auto-activation failed for order {order.yandex_order_id}: {str(e)}")
                                # Continue with just fulfillment if auto-completion fails
                        else:
                            print(f"ℹ️  Auto-activation skipped for order {order.yandex_order_id}: Order already completed")
                    else:
                        print(f"ℹ️  Auto-activation waiting for order {order.yandex_order_id}: Not all digital products have been fulfilled yet")
            else:
                print(f"⚠️  Auto-activation skipped for order {order.yandex_order_id}: The following products are missing activation templates: {', '.join(missing_templates)}")
        
        return {
            "success": True,
            "message": "Order fulfilled successfully",
            "activation_key": activation_key.key
        }
    
    def fulfill_order(self, order: models.Order) -> dict:
        """Manually fulfill an order"""
        result = self.auto_fulfill_order(order)
        
        if result["success"]:
            # Accept order on Yandex Market
            try:
                self._get_yandex_api().accept_order(order.yandex_order_id)
            except Exception as e:
                # Log error but don't fail
                print(f"Failed to accept order on Yandex Market: {str(e)}")
        
        return result
    
    def _build_activation_message(self, order: models.Order, activation_code: str) -> str:
        """Build the full activation message from template"""
        # Get product
        product = self.db.query(models.Product).filter(models.Product.id == order.product_id).first()
        if not product:
            raise ValueError("Product not found")
        
        # Get email template
        email_template = None
        if product.email_template_id:
            email_template = self.db.query(models.EmailTemplate).filter(
                models.EmailTemplate.id == product.email_template_id
            ).first()
        
        # Get app settings
        app_settings = self.db.query(models.AppSettings).first()
        if not app_settings:
            # Create default settings if they don't exist
            app_settings = models.AppSettings()
            self.db.add(app_settings)
            self.db.commit()
            self.db.refresh(app_settings)
        
        # Calculate expiry date (30 days from order creation)
        expiry_date = (order.created_at + timedelta(days=30)).strftime("%B %d, %Y")
        
        # Build message with proper spacing and paragraphs using HTML
        # Yandex API supports HTML in the slip field, so we'll use HTML for proper formatting
        html_parts = []
        
        # REMOVED: Activation code - Yandex automatically includes it in their email
        # REMOVED: "Activate the code before {expiry_date}" - Yandex handles this automatically
        
        # 1. Thank you message
        html_parts.append("<p>Thank you for your purchase!</p>")
        html_parts.append("<br>")  # Extra spacing
        
        # 2. Template body
        if email_template:
            # "To activate your subscription..." - slightly bold (using <b> instead of <strong>)
            html_parts.append("<p><b>To activate your subscription, please follow these steps:</b></p>")
            
            # Add template body - preserve structure, convert newlines to <br> tags
            template_lines = email_template.body.split('\n')
            # Process each line: preserve non-empty lines, convert to <br> separated
            template_body_lines = []
            for line in template_lines:
                line = line.strip()
                if line:  # Only add non-empty lines
                    template_body_lines.append(line)
            if template_body_lines:
                # Join with <br> to preserve line breaks within the paragraph
                template_body_html = "<br>".join(template_body_lines)
                html_parts.append(f"<p>{template_body_html}</p>")
                html_parts.append("<br>")  # One line spacing after template body
            
            # 3. Required login text (if checked)
            if email_template.required_login:
                html_parts.append("<p>Done! The operator will log in to your account and activate your subscription. Requests are processed in the order they are received.</p>")
                html_parts.append("<br>")  # One line spacing
        
        # 4. Processing time and maximum wait time (from settings) - conditional
        processing_text = None
        if app_settings.processing_time_min and app_settings.processing_time_min > 0:
            if app_settings.processing_time_max and app_settings.processing_time_max > 0:
                processing_text = f"The process typically takes {app_settings.processing_time_min}-{app_settings.processing_time_max} minutes"
            else:
                processing_text = f"The process typically takes {app_settings.processing_time_min} minutes"
            
            # Add maximum wait time if specified
            if app_settings.maximum_wait_time_value and app_settings.maximum_wait_time_value > 0 and app_settings.maximum_wait_time_unit:
                unit = app_settings.maximum_wait_time_unit
                value = app_settings.maximum_wait_time_value
                # Make unit plural if value > 1
                if value > 1 and not unit.endswith('s'):
                    unit = unit + 's'
                
                if processing_text:
                    processing_text += f", with a maximum wait time of {value} {unit}."
                else:
                    processing_text = f"Maximum wait time of {value} {unit}."
            elif processing_text:
                processing_text += "."
        
        if processing_text:
            html_parts.append(f"<p>{processing_text}</p>")
        
        # 5. Working hours (from settings) - conditional
        if app_settings.working_hours_text and app_settings.working_hours_text.strip():
            html_parts.append(f"<p>{app_settings.working_hours_text}</p>")
            html_parts.append("<br><br>")  # Two lines spacing
        
        # 6. Company email (from settings) - conditional
        # "Mail:" should be bold, email should be clickable
        if app_settings.company_email and app_settings.company_email.strip():
            email_link = f'<a href="mailto:{app_settings.company_email}">{app_settings.company_email}</a>'
            html_parts.append(f"<p><b>Mail:</b> {email_link}</p>")
        
        # Join all HTML parts - each <p> tag creates a paragraph with spacing
        html_text = "".join(html_parts)
        
        # Return HTML formatted text
        # Yandex API supports HTML in the slip field
        return html_text
    
    def complete_order_with_all_items(self, orders: List[models.Order], manual_activation_keys: Optional[Dict[int, str]] = None) -> dict:
        """Complete order by delivering digital goods for ALL items in the order
        
        Takes a list of Order records (one per item) with the same yandex_order_id
        and sends activation for all items in a single API call.
        
        Args:
            orders: List of Order records for all items in the order
            manual_activation_keys: Optional dict mapping product_id to activation key string
                                   Used when templates have random_key=False
        """
        from typing import Dict, Optional
        if not orders:
            return {"success": False, "message": "No orders provided"}
        
        # Use the first order as reference (they all share yandex_order_id, customer, etc.)
        base_order = orders[0]
        yandex_order_id = base_order.yandex_order_id
        
        # CRITICAL: Fetch fresh order details from Yandex API to get ALL items
        # According to Yandex docs, we must deliver ALL items in the order
        print(f"🔍 Fetching fresh order details from Yandex for order {yandex_order_id}")
        try:
            yandex_order_data = self._get_yandex_api().get_order(yandex_order_id)
        except Exception as e:
            print(f"⚠️  Failed to fetch order from Yandex API: {str(e)}")
            # Fallback to stored data
            yandex_order_data = base_order.yandex_order_data
            if not yandex_order_data or not isinstance(yandex_order_data, dict):
                return {"success": False, "message": f"Failed to get order details from Yandex: {str(e)}"}
        
        # Handle different response structures
        if "order" in yandex_order_data:
            order_data = yandex_order_data["order"]
        elif "orders" in yandex_order_data and len(yandex_order_data["orders"]) > 0:
            order_data = yandex_order_data["orders"][0]
        else:
            order_data = yandex_order_data
        
        items_data = order_data.get("items", [])
        if not items_data:
            return {"success": False, "message": "No items found in order data from Yandex"}
        
        print(f"🔍 Processing order {yandex_order_id} with {len(orders)} order records and {len(items_data)} Yandex items")
        print(f"   Yandex items: {[(item.get('id'), item.get('offerId'), item.get('shopSku'), item.get('digitalItem', False)) for item in items_data]}")
        
        # CRITICAL: Iterate through ALL Yandex items (not our order records)
        # Yandex requires ALL digital items to be delivered
        delivery_items = []
        processed_item_ids = set()
        
        # Create a map of order records by product_id for quick lookup
        order_by_product = {o.product_id: o for o in orders}
        
        # Iterate through ALL items from Yandex order
        for yandex_item in items_data:
            item_id = yandex_item.get("id")
            if not item_id:
                continue
            
            offer_id = yandex_item.get("offerId") or yandex_item.get("shopSku")
            shop_sku = yandex_item.get("shopSku") or yandex_item.get("offerId")
            market_sku = str(yandex_item.get("marketSku", "")) if yandex_item.get("marketSku") else None
            
            if not offer_id:
                print(f"  ⚠️  Item {item_id} has no offerId/shopSku, skipping")
                continue
            
            # Find matching product in our database
            product = self.db.query(models.Product).filter(
                (models.Product.yandex_market_id == offer_id) |
                (models.Product.yandex_market_id == shop_sku) |
                (models.Product.yandex_market_sku == offer_id) |
                (models.Product.yandex_market_sku == shop_sku)
            ).first()
            
            # Also try matching by marketSku if available
            if not product and market_sku:
                product = self.db.query(models.Product).filter(
                    (models.Product.yandex_market_sku == market_sku) |
                    (models.Product.yandex_market_id == market_sku)
                ).first()
            
            if not product:
                print(f"  ⚠️  No product found for item {item_id} (offerId: {offer_id}, shopSku: {shop_sku})")
                print(f"     This item belongs to another seller or product not synced. Skipping.")
                continue
            
            # Check if product is digital
            if product.product_type != models.ProductType.DIGITAL:
                print(f"  ℹ️  Item {item_id} product {product.name} is not digital, skipping")
                continue
            
            # Find order record for this product
            order_record = order_by_product.get(product.id)
            if not order_record:
                # Try to find by querying
                order_record = self.db.query(models.Order).filter(
                    models.Order.yandex_order_id == yandex_order_id,
                    models.Order.product_id == product.id
                ).first()
            
            if not order_record:
                print(f"  ⚠️  No order record found for product {product.name} (item {item_id})")
                print(f"     Creating temporary order record for delivery...")
                # Use get_or_create pattern to avoid duplicate key errors
                # Check again if it was created by another process
                order_record = self.db.query(models.Order).filter(
                    models.Order.yandex_order_id == yandex_order_id,
                    models.Order.product_id == product.id
                ).first()
                
                if not order_record:
                    # Create a temporary order record for this item
                    order_record = models.Order(
                    yandex_order_id=yandex_order_id,
                    product_id=product.id,
                    customer_name=base_order.customer_name,
                    customer_email=base_order.customer_email,
                    customer_phone=base_order.customer_phone,
                    quantity=yandex_item.get("count", 1),
                    total_amount=float(yandex_item.get("price", 0)) * yandex_item.get("count", 1),
                    status=models.OrderStatus.PROCESSING,
                    yandex_order_data=order_data,
                    yandex_status=order_data.get("status", "PROCESSING")
                    )
                    try:
                        self.db.add(order_record)
                        self.db.flush()
                    except Exception as e:
                        # If duplicate key error, try to get the existing record
                        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                            self.db.rollback()
                            order_record = self.db.query(models.Order).filter(
                                models.Order.yandex_order_id == yandex_order_id,
                                models.Order.product_id == product.id
                            ).first()
                            if order_record:
                                print(f"  ℹ️  Order record already exists for product {product.name}, using existing record")
                            else:
                                raise
                        else:
                            raise
            
            # Get or generate activation key
            activation_key = None
            activation_code_to_use = None  # The actual code to send to Yandex
            
            # PRIORITY 1: Check if manual activation key was provided for this product
            if manual_activation_keys and product.id in manual_activation_keys:
                manual_key = manual_activation_keys[product.id].strip()
                if manual_key:
                    # Use the provided manual key directly - don't create ActivationKey record
                    activation_code_to_use = manual_key
                    print(f"  ✅ Using manual activation key for product {product.name}: {manual_key[:20]}...")
                    
                    # Optionally create ActivationKey record for tracking (but use manual key for sending)
                    activation_key = models.ActivationKey(
                        product_id=product.id,
                        key=manual_key,
                        is_used=True,
                        used_at=datetime.utcnow()
                    )
                    self.db.add(activation_key)
                    self.db.flush()
                    order_record.activation_key_id = activation_key.id
            
            # PRIORITY 2: Check if order already has an activation key assigned
            if not activation_code_to_use and order_record.activation_key_id:
                activation_key = self.db.query(models.ActivationKey).filter(
                    models.ActivationKey.id == order_record.activation_key_id
                ).first()
                if activation_key:
                    activation_code_to_use = activation_key.key
            
            # PRIORITY 3: Generate a new key (only if no manual key was provided and no existing key)
            if not activation_code_to_use:
                import secrets
                key = f"{product.yandex_market_sku or product.id}-{secrets.token_urlsafe(16)}"
                activation_key = models.ActivationKey(
                    product_id=product.id,
                    key=key,
                    is_used=True,
                    used_at=datetime.utcnow()
                )
                self.db.add(activation_key)
                self.db.flush()
                order_record.activation_key_id = activation_key.id
                activation_code_to_use = key
                print(f"  ✅ Generated new activation key for product {product.name}")
            
            # CRITICAL: Check if product has an activation template
            # According to requirements, ALL products must have templates before sending
            if not product.email_template_id:
                print(f"  ⚠️  Product {product.name} (item {item_id}) has no activation template attached")
                print(f"     Skipping this item. Please attach an activation template to the product first.")
                continue
            
            # Build activation message for this product
            # Use the activation code we determined (manual key if provided, otherwise generated)
            activation_instructions = self._build_activation_message(order_record, activation_code_to_use)
            
            # Calculate activateTill date from email template
            activate_till_days = 30  # Default
            if product.email_template_id:
                email_template = self.db.query(models.EmailTemplate).filter(
                    models.EmailTemplate.id == product.email_template_id
                ).first()
                if email_template and email_template.activate_till_days:
                    activate_till_days = email_template.activate_till_days
            
            expiry_date = datetime.utcnow() + timedelta(days=activate_till_days)
            activate_till = expiry_date.strftime("%Y-%m-%d")
            
            # Add to delivery items
            # Use activation_code_to_use (manual key if provided, otherwise generated key)
            delivery_items.append({
                "id": int(item_id),
                "codes": [activation_code_to_use],  # Array of codes - use manual key if provided
                "slip": activation_instructions,
                "activate_till": activate_till
            })
            processed_item_ids.add(int(item_id))
            print(f"  ✅ Added item {item_id} for product {product.name} (offerId: {offer_id})")
        
        # Final check: ensure we have ALL digital items that belong to our campaign
        # Note: We only need to deliver items that belong to our campaign (i.e., match our products)
        all_digital_item_ids = {item.get("id") for item in items_data 
                               if item.get("id") and item.get("digitalItem", False)}
        missing_digital_items = all_digital_item_ids - processed_item_ids
        
        if missing_digital_items:
            # Check if missing items belong to our campaign
            missing_items_info = []
            for missing_item_id in missing_digital_items:
                missing_item = next((item for item in items_data if item.get("id") == missing_item_id), None)
                if missing_item:
                    offer_id = missing_item.get("offerId") or missing_item.get("shopSku")
                    # Check if we have a product for this item
                    product = self.db.query(models.Product).filter(
                        (models.Product.yandex_market_id == offer_id) |
                        (models.Product.yandex_market_sku == offer_id)
                    ).first()
                    if product:
                        missing_items_info.append(f"item.id={missing_item_id} (product: {product.name}, offerId: {offer_id})")
                    else:
                        missing_items_info.append(f"item.id={missing_item_id} (offerId: {offer_id} - product not found in database)")
            
            if missing_items_info:
                return {
                    "success": False, 
                    "message": f"Cannot deliver order: Missing digital content for {len(missing_digital_items)} item(s): {', '.join(missing_items_info)}. "
                              f"Please ensure all products are synced and have activation keys assigned."
                }
        
        if not delivery_items:
            return {"success": False, "message": "No items to deliver. Make sure all products have activation keys assigned and activation templates attached."}
        
        # Final validation: Check if we're missing any digital items that belong to our products
        # This ensures ALL products in the order have templates
        products_without_templates = []
        for yandex_item in items_data:
            item_id = yandex_item.get("id")
            if item_id in processed_item_ids:
                continue  # Already processed
            
            offer_id = yandex_item.get("offerId") or yandex_item.get("shopSku")
            if not offer_id:
                continue
            
            # Check if this item belongs to one of our products
            product = self.db.query(models.Product).filter(
                (models.Product.yandex_market_id == offer_id) |
                (models.Product.yandex_market_id == yandex_item.get("shopSku")) |
                (models.Product.yandex_market_sku == offer_id) |
                (models.Product.yandex_market_sku == yandex_item.get("shopSku"))
            ).first()
            
            if product and product.product_type == models.ProductType.DIGITAL:
                if not product.email_template_id:
                    products_without_templates.append(product.name)
        
        if products_without_templates:
            return {
                "success": False,
                "message": f"Cannot send activation: The following products are missing activation templates: {', '.join(products_without_templates)}. Please attach activation templates to all products before sending."
            }
        
        try:
            # Send all items in one API call
            self._get_yandex_api().deliver_digital_goods(
                order_id=yandex_order_id,
                items=delivery_items
            )
            
            # Update all order records
            # Don't hardcode status to COMPLETED - let Yandex API sync determine the status
            # Only mark activation as sent and let the sync process update status from Yandex
            for order_record in orders:
                order_record.activation_code_sent = True
                order_record.activation_code_sent_at = datetime.utcnow()
                # Status will be updated by Yandex API sync, not hardcoded here
                if not order_record.completed_at:
                    order_record.completed_at = datetime.utcnow()
            
            self.db.commit()
            
            # Trigger a status refresh from Yandex API to get the actual status
            # This ensures we get DELIVERED status if the order was delivered
            try:
                fresh_order_data = self._get_yandex_api().get_order(yandex_order_id)
                fresh_status = fresh_order_data.get("status")
                if fresh_status:
                    from app.routers.webhooks import _map_yandex_status
                    mapped_status = _map_yandex_status(fresh_status)
                    
                    # Update all order records with fresh status (unless already FINISHED)
                    all_orders_for_id = self.db.query(models.Order).filter(
                        models.Order.yandex_order_id == yandex_order_id
                    ).all()
                    
                    for order_record in all_orders_for_id:
                        # Always update yandex_status and yandex_order_data
                        order_record.yandex_status = fresh_status
                        order_record.yandex_order_data = fresh_order_data
                        
                        # CRITICAL: Never override FINISHED status except with CANCELLED
                        # FINISHED is a manual override that takes precedence over all Yandex API statuses
                        if order_record.status == models.OrderStatus.FINISHED:
                            # Only allow CANCELLED to override FINISHED
                            if mapped_status == models.OrderStatus.CANCELLED:
                                order_record.status = mapped_status
                                print(f"  ⚠️  Order {yandex_order_id}: FINISHED status overridden by CANCELLED from Yandex")
                            else:
                                # Keep FINISHED status, don't update from Yandex API
                                print(f"  ℹ️  Order {yandex_order_id}: Keeping FINISHED status (Yandex status: {fresh_status} ignored)")
                        else:
                            # Not FINISHED, update status normally
                            order_record.status = mapped_status
                    
                    self.db.commit()
                    print(f"✅ Synced order {yandex_order_id} status from Yandex API: {fresh_status} -> {mapped_status}")
            except Exception as e:
                print(f"⚠️  Could not sync order {yandex_order_id} status from Yandex API: {str(e)}")
                # Continue - activation was sent successfully
            
            return {
                "success": True, 
                "message": f"Order completed successfully - {len(delivery_items)} item(s) delivered to Yandex"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "message": f"Failed to complete order: {str(e)}"}
    
    def complete_order_with_code(self, order: models.Order, activation_code: str = None) -> dict:
        """Complete order by delivering digital goods via Yandex Market API
        
        Uses POST /campaigns/{campaignId}/orders/{orderId}/deliverDigitalGoods
        Requires item_id from order.yandex_order_data['items'][].id
        """
        # Get activation key using query
        activation_key = self.db.query(models.ActivationKey).filter(
            models.ActivationKey.id == order.activation_key_id
        ).first()
        
        if not activation_key:
            raise ValueError("Order has no activation key assigned")
        
        # Use provided code or key from database
        code_to_send = activation_code or activation_key.key
        
        try:
            # Build full activation message from template
            activation_instructions = self._build_activation_message(order, code_to_send)
            
            # Extract item_id from stored yandex_order_data
            # The item_id is required for the deliverDigitalGoods endpoint
            item_id = None
            if order.yandex_order_data and isinstance(order.yandex_order_data, dict):
                items = order.yandex_order_data.get("items", [])
                if items:
                    # Match by product's offerId, or just use the first item
                    product = self.db.query(models.Product).filter(
                        models.Product.id == order.product_id
                    ).first()
                    
                    if product:
                        for item in items:
                            if item.get("offerId") == product.yandex_market_id:
                                item_id = item.get("id")
                                break
                    
                    # Fallback: use first item's id
                    if not item_id:
                        item_id = items[0].get("id")
            
            if not item_id:
                raise ValueError(
                    "Cannot find item_id in yandex_order_data. "
                    "Try syncing orders first to get the full order data from Yandex."
                )
            
            # Calculate activateTill date from email template
            activate_till_days = 30  # Default to 30 days
            if product.email_template_id:
                email_template = self.db.query(models.EmailTemplate).filter(
                    models.EmailTemplate.id == product.email_template_id
                ).first()
                if email_template and email_template.activate_till_days:
                    activate_till_days = email_template.activate_till_days
            
            # Calculate activate_till date in YYYY-MM-DD format (date only, no time)
            # Yandex Market API requires just the date (YYYY-MM-DD), not datetime
            expiry_date = datetime.utcnow() + timedelta(days=activate_till_days)
            activate_till = expiry_date.strftime("%Y-%m-%d")
            print(f"📅 Activation code expires on: {activate_till} (in {activate_till_days} days, YYYY-MM-DD format)")
            
            # Send activation code and instructions to Yandex Market
            # Uses deliverDigitalGoods endpoint via complete_order wrapper
            self._get_yandex_api().complete_order(
                order_id=order.yandex_order_id,
                activation_code=code_to_send,
                activation_instructions=activation_instructions,
                item_id=item_id,
                activate_till=activate_till
            )
            
            # Update order - don't hardcode status, let Yandex API sync determine it
            order.activation_code_sent = True
            order.activation_code_sent_at = datetime.utcnow()
            # Status will be updated by Yandex API sync, not hardcoded here
            if not order.completed_at:
                order.completed_at = datetime.utcnow()
            self.db.commit()
            
            # Trigger a status refresh from Yandex API to get the actual status
            try:
                fresh_order_data = self.yandex_api.get_order(order.yandex_order_id)
                fresh_status = fresh_order_data.get("status")
                if fresh_status:
                    from app.routers.webhooks import _map_yandex_status
                    mapped_status = _map_yandex_status(fresh_status)
                    
                    # Always update yandex_status and yandex_order_data
                    order.yandex_status = fresh_status
                    order.yandex_order_data = fresh_order_data
                    
                    # CRITICAL: Never override FINISHED status except with CANCELLED
                    # FINISHED is a manual override that takes precedence over all Yandex API statuses
                    if order.status == models.OrderStatus.FINISHED:
                        # Only allow CANCELLED to override FINISHED
                        if mapped_status == models.OrderStatus.CANCELLED:
                            order.status = mapped_status
                            print(f"  ⚠️  Order {order.yandex_order_id}: FINISHED status overridden by CANCELLED from Yandex")
                        else:
                            # Keep FINISHED status, don't update from Yandex API
                            print(f"  ℹ️  Order {order.yandex_order_id}: Keeping FINISHED status (Yandex status: {fresh_status} ignored)")
                    else:
                        # Not FINISHED, update status normally
                        order.status = mapped_status
                        print(f"✅ Synced order {order.yandex_order_id} status from Yandex API: {fresh_status} -> {mapped_status}")
                    
                    self.db.commit()
            except Exception as e:
                print(f"⚠️  Could not sync order {order.yandex_order_id} status from Yandex API: {str(e)}")
                # Continue - activation was sent successfully
            
            return {"success": True, "message": "Order completed successfully - digital goods delivered to Yandex"}
        except Exception as e:
            return {"success": False, "message": f"Failed to complete order: {str(e)}"}
