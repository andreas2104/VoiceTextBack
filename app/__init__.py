from flask import Flask, jsonify, send_from_directory, abort, request
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
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from app.scheduler.scheduler import scheduler
import atexit

def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="../../Front/out", static_url_path="/")  

    app.url_map.strict_slashes = False
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    app.logger.info(f"Mode: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}")
    app.logger.info(f"Frontend URL: {FRONTEND_URL}")

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
        'JWT_ACCESS_COOKIE_NAME': 'access_token_cookie',
        'JWT_REFRESH_COOKIE_NAME': 'refresh_token_cookie',
        'JWT_ACCESS_TOKEN_EXPIRES': timedelta(hours=1),
        'JWT_REFRESH_TOKEN_EXPIRES': timedelta(days=30),
        'JWT_COOKIE_SECURE': IS_PRODUCTION,
        'JWT_COOKIE_HTTPONLY': True,
        'JWT_COOKIE_SAMESITE': 'None' if IS_PRODUCTION else 'Lax',
        'JWT_COOKIE_CSRF_PROTECT': False,
        'JWT_COOKIE_DOMAIN': None,
        'JWT_COOKIE_PATH': '/',
        'JWT_ACCESS_COOKIE_PATH': '/',
        'JWT_REFRESH_COOKIE_PATH': '/api/auth/refresh',
        'JWT_ALGORITHM': 'HS256',
    })

    CORS(app,
         resources={r"/api/*": {
             "origins": [FRONTEND_URL],
             "allow_credentials": True
         }},
         supports_credentials=True,
         expose_headers=["Content-Type", "Set-Cookie"],
         allow_headers=["Content-Type", "Authorization", "Cookie"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         max_age=3600)

    jwt = JWTManager(app)

    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        app.logger.warning(f" JWT unauthorized: {callback}")
        return jsonify({
            "error": "Missing or invalid token",
            "message": "Authorization required"
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        app.logger.warning(f" JWT invalid token: {callback}")
        return jsonify({
            "error": "Invalid token",
            "message": str(callback)
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.info(f"JWT expired - User: {jwt_payload.get('sub')}")
        return jsonify({
            "error": "Token expired",
            "message": "The token has expired"
        }), 401
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return False

    db.init_app(app)
    migrate.init_app(app, db)
    
    if not IS_PRODUCTION:
        with app.app_context():
            try:
                db.create_all()
                app.logger.info("Tables de base de données créées/vérifiées")
            except Exception as e:
                app.logger.error(f" Erreur création tables: {str(e)}")

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
        (auth_bp, "/api/auth"),
    ]
    
    for blueprint, prefix in blueprints:
        if prefix:
            app.register_blueprint(blueprint, url_prefix=prefix)
        else:
            app.register_blueprint(blueprint)

    app.logger.info(f"{len(blueprints)} blueprints enregistrés")

    try:
        scheduler.init_app(app)
        app.logger.info("Scheduler initialisé")

        with app.app_context():
            scheduler.start()
            app.logger.info("Scheduler démarré avec succès")

    except Exception as e:
        app.logger.error(f"Erreur initialisation/démarrage scheduler: {str(e)}", exc_info=True)

    def shutdown_scheduler():
        """Arrêter proprement le scheduler"""
        try:
            if scheduler and hasattr(scheduler, 'scheduler') and scheduler.scheduler:
                if scheduler.scheduler.running:
                    scheduler.shutdown()
                    app.logger.info("Scheduler arrêté proprement")
        except Exception as e:
            app.logger.error(f"Erreur arrêt scheduler: {str(e)}")

    atexit.register(shutdown_scheduler)
    
    @app.teardown_appcontext
    def teardown_scheduler(exception=None):
        """Cleanup du scheduler en cas d'erreur dans le contexte"""
        if exception:
            app.logger.error(f"Exception dans le contexte: {exception}")
    
    
    # @app.route('/health')
    # def health_check():
    #     """Endpoint pour vérifier la santé de l'application"""
    #     scheduler_status = "running" if (scheduler and hasattr(scheduler, 'scheduler') 
    #                                     and scheduler.scheduler and scheduler.scheduler.running) else "stopped"
        
    #     return jsonify({
    #         "status": "healthy",
    #         "environment": "production" if IS_PRODUCTION else "development",
    #         "scheduler": scheduler_status,
    #         "database": "connected"
    #     }), 200

    @app.before_request
    def try_files_middleware():
        print("H", request.path)
        # Ignore API routes
        if request.path.startswith("/api/"):
            return None

        path = os.path.join(app.static_folder, request.path.lstrip("/"))
        print(os.path.realpath(path))

        if request.path == "/":
            return send_from_directory(app.static_folder, "index.html")

        # Try the requested path
        if os.path.isfile(path):
            return send_from_directory(app.static_folder, request.path.lstrip("/"))

        # Try adding .html
        html_path = path + ".html"
        if os.path.isfile(html_path):
            return send_from_directory(app.static_folder, request.path.lstrip("/") + ".html")

        # Try as a directory (serve index.html)
        if os.path.isdir(path):
            index_path = os.path.join(path, "index.html")
            if os.path.isfile(index_path):
                return send_from_directory(path, "index.html")

        # If nothing matches, return  # Only for non-API routes
        if not request.path.startswith("/api/"):
            abort(404)

    return app