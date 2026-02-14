import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from jinja2 import Template
from typing import Optional
from app import models
from app.config import settings


class EmailService:
    """Service for sending emails"""
    
    def __init__(self, business_id: int, db=None):
        """Initialize EmailService with SMTP settings from database
        
        Args:
            business_id: The business ID to get settings for (required)
            db: Optional database session (will create one if not provided)
        """
        if not business_id:
            raise ValueError("business_id is required. Each business must configure their own SMTP settings.")
        
        # Get settings from database for this business
        if db is None:
            from app.database import SessionLocal
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            from app.services.config_validator import validate_smtp_config
            app_settings = validate_smtp_config(business_id, db)
            
            # Use database settings only
            self.smtp_host = app_settings.smtp_host.strip() if app_settings.smtp_host else None
            self.smtp_port = app_settings.smtp_port if app_settings.smtp_port else 587
            # Use smtp_user if set, otherwise fall back to from_email (they're usually the same)
            self.smtp_user = (app_settings.smtp_user.strip() if app_settings.smtp_user else None) or (app_settings.from_email.strip() if app_settings.from_email else None)
            self.smtp_password = app_settings.smtp_password.strip() if app_settings.smtp_password else None
            self.from_email = app_settings.from_email.strip() if app_settings.from_email else None
        finally:
            if close_db:
                db.close()
    
    def _get_email_template(self, order: models.Order, db) -> str:
        """Get email template for order"""
        # Get product using query
        product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
        if not product:
            # Default template if product not found
            template_subject = "Digital Product Activation Code"
            template_body = """
            <html>
            <body>
                <h2>Digital Product Activation</h2>
                <p>Hello, {{ customer_name }}!</p>
                <p>Here is your activation code for the digital product from your order.</p>
                <p><strong>Order Number:</strong> {{ order_number }}</p>
                <p><strong>Product:</strong> {{ product_name }}</p>
                <p><strong>Activation Code:</strong> {{ activation_code }}</p>
                <p><strong>Activate before:</strong> {{ expiry_date }}</p>
                <p>Thank you for your purchase!</p>
                {% if instructions %}
                <h3>Activation Instructions:</h3>
                <div>{{ instructions }}</div>
                {% endif %}
            </body>
            </html>
            """
            return template_subject, template_body
        
        # Use product's email template if available
        email_template = None
        if product.email_template_id:
            email_template = db.query(models.EmailTemplate).filter(
                models.EmailTemplate.id == product.email_template_id
            ).first()
        
        if email_template:
            template_body = email_template.body
            template_subject = email_template.subject
        else:
            # Default template
            template_subject = "Digital Product Activation Code"
            template_body = """
            <html>
            <body>
                <h2>Digital Product Activation</h2>
                <p>Hello, {{ customer_name }}!</p>
                <p>Here is your activation code for the digital product from your order.</p>
                <p><strong>Order Number:</strong> {{ order_number }}</p>
                <p><strong>Product:</strong> {{ product_name }}</p>
                <p><strong>Activation Code:</strong> {{ activation_code }}</p>
                <p><strong>Activate before:</strong> {{ expiry_date }}</p>
                <p>Thank you for your purchase!</p>
                {% if instructions %}
                <h3>Activation Instructions:</h3>
                <div>{{ instructions }}</div>
                {% endif %}
            </body>
            </html>
            """
        
        return template_subject, template_body
    
    def _render_template(self, template: str, context: dict) -> str:
        """Render Jinja2 template with context"""
        jinja_template = Template(template)
        return jinja_template.render(**context)
    
    def send_activation_email(self, order: models.Order, db, custom_instructions: Optional[str] = None) -> dict:
        """Send activation email to customer
        
        Note: Yandex Market typically handles sending activation emails automatically.
        This function is only useful if:
        1. Customer provided their email in chat and you want to send additional messages
        2. You want to send custom follow-up emails outside of Yandex's system
        """
        if not order.customer_email:
            return {"success": False, "message": "Customer email not provided. Email addresses are usually not available from Yandex Market API. You can add the email manually if the customer provides it in chat."}
        
        # Get activation key using query
        activation_key = db.query(models.ActivationKey).filter(
            models.ActivationKey.id == order.activation_key_id
        ).first()
        
        if not activation_key:
            return {"success": False, "message": "Order has no activation key"}
        
        # Get product using query
        product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
        if not product:
            return {"success": False, "message": "Product not found"}
        
        # Get email template
        subject, body_template = self._get_email_template(order, db)
        
        # Calculate expiry date (30 days from now)
        expiry_date = (datetime.utcnow() + timedelta(days=30)).strftime("%B %d, %Y")
        
        # Prepare context
        context = {
            "customer_name": order.customer_name or "Customer",
            "order_number": order.yandex_order_id,
            "product_name": product.name,
            "activation_code": activation_key.key,
            "expiry_date": expiry_date,
            "instructions": custom_instructions or product.description
        }
        
        # Render template
        html_body = self._render_template(body_template, context)
        rendered_subject = self._render_template(subject, context)
        
        # Send email
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = rendered_subject
            msg["From"] = self.from_email
            msg["To"] = order.customer_email
            
            msg.attach(MIMEText(html_body, "html"))
            
            if not self.smtp_host or not self.smtp_user:
                # In development, just log the email
                print(f"Email would be sent to {order.customer_email}")
                print(f"Subject: {rendered_subject}")
                print(f"Body: {html_body}")
                return {"success": True, "message": "Email logged (SMTP not configured)"}
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            # Update order
            order.activation_code_sent = True
            order.activation_code_sent_at = datetime.utcnow()
            db.commit()
            
            return {"success": True, "message": "Activation email sent successfully"}
        except Exception as e:
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True
    ) -> dict:
        """Send a simple email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            is_html: Whether body is HTML (default: True)
        
        Returns:
            dict with 'success' and 'message' keys
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
            
            if not self.smtp_host or not self.smtp_user:
                # In development, just log the email
                print(f"📧 Email would be sent to {to_email}")
                print(f"   Subject: {subject}")
                print(f"   Body: {body}")
                return {
                    "success": True,
                    "message": "Email logged (SMTP not configured)"
                }
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return {"success": True, "message": "Email sent successfully"}
        except Exception as e:
            import traceback
            print(f"⚠️  Error sending email to {to_email}: {str(e)}")
            print(traceback.format_exc())
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    def send_marketing_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        attachments: Optional[list] = None
    ) -> dict:
        """Send a marketing email to a client
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML)
            attachments: Optional list of attachment dicts with 'url', 'type', 'name'
        
        Returns:
            dict with 'success' and 'message' keys
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            msg.attach(MIMEText(body, "html"))
            
            # Handle attachments if provided
            if attachments:
                from email.mime.base import MIMEBase
                from email import encoders
                import requests
                import os
                from pathlib import Path
                
                for attachment in attachments:
                    try:
                        # Download attachment if it's a URL
                        if attachment.get("url"):
                            url = attachment["url"]
                            # If it's a relative URL, make it absolute
                            if url.startswith("/"):
                                # Assume it's a media file from our server
                                from app.config import settings
                                url = f"{settings.PUBLIC_URL}{url}"
                            
                            response = requests.get(url, timeout=10)
                            if response.status_code == 200:
                                attachment_part = MIMEBase('application', 'octet-stream')
                                attachment_part.set_payload(response.content)
                                encoders.encode_base64(attachment_part)
                                attachment_part.add_header(
                                    'Content-Disposition',
                                    f'attachment; filename= {attachment.get("name", "attachment")}'
                                )
                                msg.attach(attachment_part)
                    except Exception as e:
                        print(f"⚠️  Warning: Could not attach {attachment.get('name', 'file')}: {str(e)}")
                        continue
            
            if not self.smtp_host or not self.smtp_user:
                # In development, just log the email
                print(f"📧 Email would be sent to {to_email}")
                print(f"   Subject: {subject}")
                print(f"   Body length: {len(body)} characters")
                if attachments:
                    print(f"   Attachments: {len(attachments)} file(s)")
                return {
                    "success": True, 
                    "message": "Email logged (SMTP not configured). Configure SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in .env to send actual emails."
                }
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return {"success": True, "message": "Marketing email sent successfully"}
        except Exception as e:
            import traceback
            print(f"⚠️  Error sending marketing email to {to_email}: {str(e)}")
            print(traceback.format_exc())
            return {"success": False, "message": f"Failed to send email: {str(e)}"}