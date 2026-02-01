from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://yandex_user:yandex_password@postgres:5432/yandex_market"
    
    # Yandex Market API
    YANDEX_MARKET_API_TOKEN: Optional[str] = None
    YANDEX_MARKET_CAMPAIGN_ID: Optional[str] = None
    YANDEX_MARKET_API_URL: str = "https://api.partner.market.yandex.ru"
    
    # Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@market.yandex.ru"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Public URL for media files (used when uploading to Yandex)
    PUBLIC_URL: str = "http://localhost:8000"
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None  # Your Telegram chat ID for notifications
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
