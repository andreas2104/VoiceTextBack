from flask import Flask
from flask_cors import CORS
from .extensions import db, migrate, jwt
from app.routes.utilisateur_routes import utilisateur_bp
from app.routes.projet_routes import projet_bp
from app.routes.modelIA_routes import modelIA_bp
from app.routes.template_routes import template_bp
from app.routes.prompt_routes import prompt_bp
from app.routes.generateur_routes import ollama_bp
from app.routes.contenu_routes import contenu_bp
# from app.routes.auth_routes import auth_bp
from dotenv import load_dotenv
import os


def create_app():
    load_dotenv()

    app = Flask(__name__)

    # Configuration de la clé secrète
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "default_secret_key")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Configuration JWT
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = False  # À définir à True en production avec HTTPS
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True

    # Validation des variables d'environnement
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        raise ValueError("La variable d'environnement DB_URL n'est pas définie.")
    if not app.config['JWT_SECRET_KEY']:
        raise ValueError("La variable d'environnement JWT_SECRET_KEY n'est pas définie.")

    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Création des tables (optionnel, peut être géré par Flask-Migrate)
    with app.app_context():
        db.create_all()

    # Configuration CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Enregistrement des blueprints
    app.register_blueprint(utilisateur_bp, url_prefix='/api/utilisateurs')
    app.register_blueprint(projet_bp, url_prefix='/api/projets')
    app.register_blueprint(modelIA_bp, url_prefix='/api/modelIA')
    app.register_blueprint(template_bp, url_prefix='/api/templates')
    app.register_blueprint(prompt_bp, url_prefix='/api/prompts')
    app.register_blueprint(ollama_bp, url_prefix='/api/generer')
    app.register_blueprint(contenu_bp, url_prefix="/api/contenu")
    # app.register_blueprint(auth_bp, url_prefix="/api/auth")

    return app