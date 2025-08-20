from flask import Flask, jsonify
from flask_cors import CORS
from .extensions import db, migrate, jwt
from app.routes.utilisateur_routes import utilisateur_bp
from app.routes.projet_routes import projet_bp
from app.routes.modelIA_routes import modelIA_bp
from app.routes.template_routes import template_bp
from app.routes.prompt_routes import prompt_bp
from app.routes.generateur_routes import ollama_bp
from app.routes.contenu_routes import contenu_bp
from app.routes.auth_routes import auth_bp 
from dotenv import load_dotenv
import os
from datetime import datetime,timedelta

# Une liste pour stocker les tokens révoqués (en mémoire)
# Pour une application en production, il est fortement recommandé d'utiliser une base de données, comme Redis
revoked_tokens = set()

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
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    
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
    app.register_blueprint(auth_bp, url_prefix="/api/auth") 

    # Ajouter le callback pour vérifier si un token est dans la blocklist
    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return jti in revoked_tokens

    # Ajouter les gestionnaires d'erreurs pour une meilleure expérience utilisateur
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"message": "The token has expired", "error": "token_expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"message": "Signature verification failed", "error": "invalid_token"}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"message": "Request does not contain an access token", "error": "authorization_required"}), 401

    return app

