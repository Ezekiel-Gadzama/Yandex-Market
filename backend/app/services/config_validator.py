"""
Configuration validation helper to check if business settings are configured
"""
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from app import models
from app.database import SessionLocal
from app.auth import get_business_id


class ConfigurationError(Exception):
    """Raised when business configuration is missing"""
    def __init__(self, message: str, missing_fields: List[str]):
        self.message = message
        self.missing_fields = missing_fields
        super().__init__(self.message)


def get_business_settings(business_id: int, db) -> Optional[models.AppSettings]:
    """Get business settings for a given business_id"""
    return db.query(models.AppSettings).filter(
        models.AppSettings.business_id == business_id
    ).first()


def validate_yandex_config(business_id: int, db) -> models.AppSettings:
    """Validate that Yandex Market API configuration is set up for the business
    
    Raises:
        ConfigurationError: If configuration is missing
        HTTPException: If settings don't exist
    """
    settings = get_business_settings(business_id, db)
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CONFIGURATION_REQUIRED",
                "message": "Business settings not found. Please configure your settings in the Settings page.",
                "missing_fields": ["yandex_api_token", "yandex_business_id"],
                "action_required": "Please go to Settings page and configure Yandex Market API credentials."
            }
        )
    
    missing_fields = []
    
    if not settings.yandex_api_token or not settings.yandex_api_token.strip():
        missing_fields.append("yandex_api_token")
    
    # Check business_id for OAuth tokens, campaign_id for ACMA tokens
    is_acma_token = settings.yandex_api_token and settings.yandex_api_token.startswith("ACMA:")
    
    if is_acma_token:
        if not settings.yandex_campaign_id or not settings.yandex_campaign_id.strip():
            missing_fields.append("yandex_campaign_id")
    else:
        if not settings.yandex_business_id or not settings.yandex_business_id.strip():
            missing_fields.append("yandex_business_id")
    
    if missing_fields:
        raise ConfigurationError(
            "Yandex Market API configuration is incomplete. Please configure your settings in the Settings page.",
            missing_fields
        )
    
    return settings


def validate_smtp_config(business_id: int, db) -> models.AppSettings:
    """Validate that SMTP configuration is set up for the business
    
    Raises:
        ConfigurationError: If configuration is missing
        HTTPException: If settings don't exist
    """
    settings = get_business_settings(business_id, db)
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CONFIGURATION_REQUIRED",
                "message": "Business settings not found. Please configure your settings in the Settings page.",
                "missing_fields": ["smtp_host", "smtp_user", "smtp_password"],
                "action_required": "Please go to Settings page and configure SMTP email settings."
            }
        )
    
    missing_fields = []
    
    if not settings.smtp_host or not settings.smtp_host.strip():
        missing_fields.append("smtp_host")
    
    # smtp_user can fall back to from_email, so check if either is set
    smtp_user = (settings.smtp_user and settings.smtp_user.strip()) or (settings.from_email and settings.from_email.strip())
    if not smtp_user:
        missing_fields.append("smtp_user")
    
    if not settings.smtp_password or not settings.smtp_password.strip():
        missing_fields.append("smtp_password")
    
    if not settings.from_email or not settings.from_email.strip():
        missing_fields.append("from_email")
    
    if missing_fields:
        raise ConfigurationError(
            "SMTP email configuration is incomplete. Please configure your email settings in the Settings page.",
            missing_fields
        )
    
    return settings


def format_config_error_response(error: ConfigurationError) -> Dict:
    """Format configuration error for API response"""
    return {
        "error": "CONFIGURATION_REQUIRED",
        "message": error.message,
        "missing_fields": error.missing_fields,
        "action_required": "Please go to Settings page and configure the missing settings, or contact your administrator."
    }
