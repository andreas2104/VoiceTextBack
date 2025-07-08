from flask import Flask
from .extensions import db, migrate
from app.routes.api_routes import api_bp

# from .routes import 

def create_app():
  app = Flask(__name__)
  app.config.from_object('config.Config')

  db.init_app(app)
  migrate.init_app(app, db)
  
  app.register_blueprint(api_bp, url_prefix='/api/users')

  return app