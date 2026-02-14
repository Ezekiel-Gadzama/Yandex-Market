"""
Script to create initial data (default email template and app settings)
Run this after database is created
"""
from app.database import SessionLocal
from app import models


def create_default_settings():
    """Create default app settings for each admin if they don't exist"""
    db = SessionLocal()
    try:
        # Get all admin users
        admins = db.query(models.User).filter(models.User.is_admin == True).all()
        
        if not admins:
            print("No admin users found. Skipping default settings creation.")
            return
        
        # Create default settings for each admin's business
        for admin in admins:
            existing = db.query(models.AppSettings).filter(
                models.AppSettings.business_id == admin.id
            ).first()
            
            if existing:
                continue
            
            default_settings = models.AppSettings(
                business_id=admin.id,
                processing_time_min=20,
                processing_time_max=30,
                maximum_wait_time_value=6,
                maximum_wait_time_unit="hours",
                working_hours_text="We are open seven days a week from 10:00 AM to 12:00 AM Moscow time.",
            )
            db.add(default_settings)
        
        db.commit()
        print("Default app settings created successfully for all admins")
    except Exception as e:
        print(f"Error creating default settings: {str(e)}")
        db.rollback()
    finally:
        db.close()


def create_default_email_template():
    """Create a default email template for digital products for each admin"""
    db = SessionLocal()
    try:
        # Get all admin users
        admins = db.query(models.User).filter(models.User.is_admin == True).all()
        
        if not admins:
            print("No admin users found. Skipping default email template creation.")
            return
        
        # Create default template for each admin's business
        for admin in admins:
            # Check if default template already exists for this business
            existing = db.query(models.EmailTemplate).filter(
                models.EmailTemplate.name == "Default Digital Product Template",
                models.EmailTemplate.business_id == admin.id
            ).first()
            
            if existing:
                continue
            
            default_template = models.EmailTemplate(
                name="Default Digital Product Template",
                body="""1. Send your registered email to the order chat on the Market. Within few minutes you will get an OTP to your email to login to your account, you need to send the OTP code to the order chat.""",
                random_key=True,
                required_login=False,
                business_id=admin.id
            )
            
            db.add(default_template)
        
        db.commit()
        print("Default email template created successfully for all admins")
    except Exception as e:
        print(f"Error creating default template: {str(e)}")
        db.rollback()
    finally:
        db.close()


def create_default_marketing_email_template():
    """Create a default marketing email template for each admin"""
    db = SessionLocal()
    try:
        # Get all admin users
        admins = db.query(models.User).filter(models.User.is_admin == True).all()
        
        if not admins:
            print("No admin users found. Skipping default marketing template creation.")
            return
        
        # Create default template for each admin's business
        for admin in admins:
            # Check if default marketing template already exists for this business
            existing = db.query(models.MarketingEmailTemplate).filter(
                models.MarketingEmailTemplate.is_default == True,
                models.MarketingEmailTemplate.business_id == admin.id
            ).first()
            
            if existing:
                continue
            
            default_template = models.MarketingEmailTemplate(
                name="Default Marketing Template",
                subject="Your Subscription Has Expired",
                body="<p>Additional information to add to the broadcasted email.</p>",
                is_default=True,
                auto_broadcast_enabled=False,
                frequency_days=None,
                business_id=admin.id
            )
            
            db.add(default_template)
        
        db.commit()
        print("Default marketing email template created successfully for all admins")
    except Exception as e:
        print(f"Error creating default marketing template: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_default_email_template()
