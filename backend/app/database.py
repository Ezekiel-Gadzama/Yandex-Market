from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from app.config import settings

# URL-encode password if it contains special characters
def encode_database_url(url: str) -> str:
    """Encode password in database URL if needed"""
    if "://" not in url:
        return url
    
    parts = url.split("://", 1)
    scheme = parts[0]
    rest = parts[1]
    
    if "@" in rest:
        auth_part, db_part = rest.rsplit("@", 1)
        if ":" in auth_part:
            user, password = auth_part.split(":", 1)
            # URL encode the password
            password_encoded = quote_plus(password)
            return f"{scheme}://{user}:{password_encoded}@{db_part}"
    
    return url

# Create PostgreSQL engine with URL-encoded password
database_url = encode_database_url(settings.DATABASE_URL)
engine = create_engine(
    database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
