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
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
    
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
