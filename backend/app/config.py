from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Allow extra env vars (e.g. POSTGRES_USER, POSTGRES_PASSWORD) from .env
    )

    # Database
    DATABASE_URL: str = "postgresql://yandex_user:yandex_password@postgres:5432/yandex_market"
    
    # Note: Yandex Market API and SMTP settings are now configured per business in the Settings page
    # Each business must configure their own Yandex API credentials and SMTP settings
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Public URL for media files (used when uploading to Yandex)
    PUBLIC_URL: str = "http://localhost:8000"


settings = Settings()
