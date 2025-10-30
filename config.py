from dotenv import load_dotenv
from celery.schedules import crontab

import os


load_dotenv()

class Config: 
  SQLALCHEMY_DATABASE_URI = os.getenv("DB_URL")
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SESSION_COOKIE_SECURE = False  # Permet les cookies sur HTTP en local
  SESSION_COOKIE_SAMESITE = 'Lax'  # Moins strict pour le dev
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_DOMAIN = None

  CELERY_BEAT_SCHEDULE = {
    'verifier-publication-en-retard':{
      'task': 'tasks.publication_tasks.verifier_publications_en_retard', 
      "schedule": crontab(minute='*/5'),
    },
    'nettoyer-anciennes-tache': {
      'task': 'app.tasks.nettoyer_anciennes_taches',
      'schedule': crontab(hour=2, minute=0),
    },
  }