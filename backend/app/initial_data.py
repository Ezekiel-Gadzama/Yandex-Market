"""
Script to create initial data (default email template and app settings)
Run this after database is created
"""
from app.database import SessionLocal
from app import models


def create_default_settings():
    """Create default app settings if they don't exist"""
    db = SessionLocal()
    try:
        existing = db.query(models.AppSettings).first()
        if existing:
            print("App settings already exist")
            return
        
        default_settings = models.AppSettings(
            processing_time_min=20,
            processing_time_max=30,
            maximum_wait_time_value=6,
            maximum_wait_time_unit="hours",
            working_hours_text="We are open seven days a week from 10:00 AM to 12:00 AM Moscow time.",
            company_email="oneplayinfo@gmail.com"
        )
        db.add(default_settings)
        db.commit()
        print("Default app settings created successfully")
    except Exception as e:
        print(f"Error creating default settings: {str(e)}")
        db.rollback()
    finally:
        db.close()


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
            body="""1. Send your registered email to the order chat on the Market. Within few minutes you will get an OTP to your email to login to your account, you need to send the OTP code to the order chat.""",
            random_key=True,
            required_login=False
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
