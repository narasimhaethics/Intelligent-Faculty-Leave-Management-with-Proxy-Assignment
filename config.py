

'''class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///faculty_management.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False'''

import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "53378446272")
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user_42wh3555w:p42wh3555w@ocdb.app:5051/db_42wh3555w"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

