"""
Script to initialize database and create default data
"""
import uvicorn
from app.database import engine, Base
from app import models
from app.initial_data import create_default_email_template

if __name__ == "__main__":
    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create default email template
    print("Creating default email template...")
    create_default_email_template()
    
    # Run the server
    print("Starting server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
