import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///faculty_management.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
