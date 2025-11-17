from dotenv import load_dotenv


import os


load_dotenv()

class Config: 
  SQLALCHEMY_DATABASE_URI = os.getenv("DB_URL")
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SESSION_COOKIE_SECURE = False  # Permet les cookies sur HTTP en local
  SESSION_COOKIE_SAMESITE = 'Lax'  # Moins strict pour le dev
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_DOMAIN = None

