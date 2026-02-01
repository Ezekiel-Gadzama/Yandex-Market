"""
Script to create initial data (default email template)
Run this after database is created
"""
from app.database import SessionLocal
from app import models


def create_default_email_template():
    """Create a default email template for digital products"""
    db = SessionLocal()
    try:
        # Check if default template already exists
        existing = db.query(models.EmailTemplate).filter(
            models.EmailTemplate.name == "Default Digital Product Template"
        ).first()
        
        if existing:
            print("Default email template already exists")
            return
        
        default_template = models.EmailTemplate(
            name="Default Digital Product Template",
            subject="Digital Product Activation Code - Order {order_number}",
            body="""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Digital Product Activation</h2>
        <p>Hello, {customer_name}!</p>
        <p>Here is your activation code for the digital product from your order.</p>
        
        <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Order Number:</strong> {order_number}</p>
            <p style="margin: 5px 0;"><strong>Product:</strong> {product_name}</p>
            <p style="margin: 5px 0;"><strong>Activation Code:</strong> <span style="font-size: 18px; font-weight: bold; color: #007bff;">{activation_code}</span></p>
            <p style="margin: 5px 0;"><strong>Activate before:</strong> {expiry_date}</p>
        </div>
        
        <p>Thank you for your purchase!</p>
        
        {instructions}
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">
            If you have any questions, please contact us through the order chat on Yandex Market.
        </p>
    </div>
</body>
</html>
            """.strip()
        )
        
        db.add(default_template)
        db.commit()
        print("Default email template created successfully")
    except Exception as e:
        print(f"Error creating default template: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_default_email_template()
