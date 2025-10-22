from flask import Flask, jsonify

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .extensions import db, migrate
from app.routes.utilisateur_routes import utilisateur_bp
from app.routes.projet_routes import projet_bp
from app.routes.modelIA_routes import modelIA_bp
from app.routes.template_routes import template_bp
from app.routes.prompt_routes import prompt_bp
from app.routes.contenu_routes import contenu_bp
from app.routes.oaut_routes import oauth_bp 
from app.routes.auth_routes import auth_bp
from app.routes.plateforme_routes import plateforme_config_bp
from app.routes.utilisateur_plateforme_routes import utilisateur_plateforme_bp
from app.routes.historique_routes import historique_bp  
from app.routes.publication_routes import publication_bp
from dotenv import load_dotenv
import os
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.url_map.strict_slashes = False
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config.update({
        'SECRET_KEY': os.getenv("SECRET_KEY", "default_secret_key"),
        'JWT_SECRET_KEY': os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key"),
        'SQLALCHEMY_DATABASE_URI': os.getenv("DB_URL"),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 10,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'max_overflow': 20
        },
        'JWT_TOKEN_LOCATION': ['cookies'], 
        'JWT_ACCESS_COOKIE_NAME': 'access_token',
        'JWT_REFRESH_COOKIE_NAME': 'refresh_token',
        'JWT_ACCESS_TOKEN_EXPIRES': 3600,  
        'JWT_REFRESH_TOKEN_EXPIRES': 30 * 24 * 3600, 
        'JWT_COOKIE_SECURE': False,  
        'JWT_COOKIE_HTTPONLY': True,  
        'JWT_COOKIE_SAMESITE': 'Lax',  
        'JWT_COOKIE_CSRF_PROTECT': False,
        'JWT_COOKIE_DOMAIN': None, 
         'JWT_COOKIE_PATH': '/',  
        'JWT_ACCESS_COOKIE_PATH': '/',  
        'JWT_REFRESH_COOKIE_PATH': '/', 
        'JWT_ALGORITHM': 'HS256',
    })
    
    
    CORS(app,
         resources={r"/api/*": {"origins": ["http://localhost:3000"]}},
         supports_credentials=True,
         expose_headers=["Content-Type", "Set-Cookie"], 
         allow_headers=["Content-Type", "Authorization", "Cookie"],  
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         max_age=3600)

    jwt = JWTManager(app)
    

    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({
            "error": "Missing or invalid token",
            "message": "Authorization required"
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({
            "error": "Invalid token",
            "message": str(callback)
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "Token expired",
            "message": "The token has expired"
        }), 401
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return False
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    if app.config.get('ENV') != 'production':
        with app.app_context():
            db.create_all()
    
    # Enregistrer les blueprints
    blueprints = [
        (utilisateur_bp, '/api/utilisateurs'),
        (projet_bp, '/api/projets'),
        (modelIA_bp, '/api/modelIA'),
        (template_bp, '/api/templates'),
        (prompt_bp, '/api/prompts'),
        (contenu_bp, "/api/contenu"),
        (plateforme_config_bp, "/api/adminplateformes"),  
        (utilisateur_plateforme_bp, "/api/plateformes"),    
        (historique_bp, "/api/historiques"),       
        (publication_bp, "/api/publications"),
        (oauth_bp, "/api/oauth"),  
        (auth_bp, "/api/auth")
    ]
    
    for blueprint, prefix in blueprints:
        if prefix:
            app.register_blueprint(blueprint, url_prefix=prefix)
        else:
            app.register_blueprint(blueprint)

    return app