from dotenv import load_dotenv

import os


load_dotenv()

class Config: 
  SQLALCHEMY_DATABASE_URI = os.getenv("DB_URL")
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
  FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
  FACEBOOK_REDIRECT_URI = os.environ.get('FACEBOOK_REDIRECT_URI')