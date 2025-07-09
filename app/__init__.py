from flask import Flask
from .extensions import db, migrate
from app.routes.utilisateur_routes import utilisateur_bp
from app.routes.projet_routes import projet_bp
from dotenv import load_dotenv
import os

def create_app():
  load_dotenv()

  app = Flask(__name__)

  app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URL")
  app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  

  db.init_app(app)
  migrate.init_app(app, db)
  with app.app_context():
    db.create_all()
  
  app.register_blueprint(utilisateur_bp, url_prefix='/api/utilisateurs')
  app.register_blueprint(projet_bp, url_prefix='/api/projets')

  return app