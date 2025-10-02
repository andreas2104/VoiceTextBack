from flask import Blueprint, redirect, request, jsonify, current_app
import requests
import jwt
import datetime
import os
from urllib.parse import urlencode, quote_plus
from app.extensions import db
from app.models.utilisateur import Utilisateur, TypeCompteEnum

oauth_bp = Blueprint('oauth_bp', __name__)

# Configuration OAuth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/oauth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Gestion des emails admin améliorée
ADMIN_EMAILS = []
admin_emails_env = os.getenv("ADMIN_EMAILS", "")
if admin_emails_env:
    ADMIN_EMAILS = [email.strip().lower() for email in admin_emails_env.split(',') if email.strip()]

# URLs Google OAuth
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

@oauth_bp.route('/login/google', methods=['GET'])
def login_google():
    """Initier la connexion Google OAuth"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return jsonify({"error": "Google OAuth not configured properly"}), 500
    
    params = {
        "response_type": "code",
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)

@oauth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Gérer le callback Google OAuth avec création/mise à jour utilisateur"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    frontend_callback_url = f"{FRONTEND_URL}/authGoogleCallback"
    
    if error:
        error_url = f"{frontend_callback_url}?error={quote_plus(error)}"
        return redirect(error_url)
    
    if not code:
        error_url = f"{frontend_callback_url}?error=no_code"
        return redirect(error_url)
    
    try:
        # Échanger le code contre un token d'accès
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        token_res = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10)
        token_json = token_res.json()
        
        if "error" in token_json:
            error_url = f"{frontend_callback_url}?error=token_exchange_failed"
            return redirect(error_url)
        
        access_token = token_json.get("access_token")
        if not access_token:
            error_url = f"{frontend_callback_url}?error=no_access_token"
            return redirect(error_url)
        
        # Récupérer les informations utilisateur depuis Google
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        
        if user_res.status_code != 200:
            error_url = f"{frontend_callback_url}?error=user_info_failed"
            return redirect(error_url)
            
        user_info = user_res.json()
        email = user_info.get("email", "").lower()
        
        if not email:
            error_url = f"{frontend_callback_url}?error=no_email"
            return redirect(error_url)
        
        if not user_info.get("verified_email", False):
            error_url = f"{frontend_callback_url}?error=email_not_verified"
            return redirect(error_url)
        
        is_admin = email in ADMIN_EMAILS
        
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        
        if not utilisateur:
            try:
                full_name = user_info.get("name", "")
                name_parts = full_name.split(' ', 1) if full_name else ["", ""]
                prenom = name_parts[0] if len(name_parts) > 0 else ""
                nom = name_parts[1] if len(name_parts) > 1 else ""
                
                utilisateur = Utilisateur(
                    email=email,
                    nom=nom,
                    prenom=prenom,
                    photo=user_info.get("picture"), # Ajout de la photo ici
                    type_compte=TypeCompteEnum.admin if is_admin else TypeCompteEnum.user,
                    mot_de_passe=None
                )
                
                db.session.add(utilisateur)
                db.session.commit()
                
                if is_admin:
                    current_app.logger.info(f"Nouveau compte admin créé pour: {email}")
                    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erreur création utilisateur {email}: {str(e)}")
                error_url = f"{frontend_callback_url}?error=database_error"
                return redirect(error_url)
        else:
            try:
                # Mise à jour de la photo pour un utilisateur existant
                if user_info.get("picture") and utilisateur.photo != user_info.get("picture"):
                    utilisateur.photo = user_info.get("picture")
                
                if is_admin and utilisateur.type_compte != TypeCompteEnum.admin:
                    utilisateur.type_compte = TypeCompteEnum.admin
                    current_app.logger.info(f"Utilisateur {email} promu admin")
                elif not is_admin and utilisateur.type_compte == TypeCompteEnum.admin:
                    pass
                
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erreur mise à jour utilisateur {email}: {str(e)}")
                error_url = f"{frontend_callback_url}?error=database_error"
                return redirect(error_url)
        
        # Générer le JWT avec les informations utilisateur
        token_payload = {
            "user_id": utilisateur.id,
            "email": email,
            "name": user_info.get("name", ""),
            "prenom": utilisateur.prenom,
            "nom": utilisateur.nom,
            "picture": utilisateur.photo, 
            "type_compte": utilisateur.type_compte.value,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        }
        
        secret_key = current_app.config.get("SECRET_KEY")
        if not secret_key:
            error_url = f"{frontend_callback_url}?error=server_config_error"
            return redirect(error_url)
            
        token = jwt.encode(token_payload, secret_key, algorithm="HS256")
        
        success_url = f"{frontend_callback_url}?token={token}"
        current_app.logger.info(f"=== CALLBACK GOOGLE RÉUSSI ===")
        current_app.logger.info(f"Utilisateur: {email}")
        current_app.logger.info(f"Type compte: {utilisateur.type_compte.value}")
        current_app.logger.info(f"Redirection vers: {frontend_callback_url}")
        current_app.logger.info(f"Token généré (longueur): {len(token)}")
        return redirect(success_url)
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur réseau OAuth: {str(e)}")
        error_url = f"{frontend_callback_url}?error=network_error"
        return redirect(error_url)
    except jwt.InvalidTokenError as e:
        current_app.logger.error(f"Erreur JWT: {str(e)}")
        error_url = f"{frontend_callback_url}?error=jwt_error"
        return redirect(error_url)
    except Exception as e:
        current_app.logger.error(f"Erreur inattendue OAuth: {str(e)}")
        error_url = f"{frontend_callback_url}?error=unexpected_error"
        return redirect(error_url)

@oauth_bp.route('/google/callback/api', methods=['GET'])
def google_callback_api():
    """Version API du callback qui retourne JSON (optionnel)"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return jsonify({"error": f"Google OAuth error: {error}"}), 400
    
    if not code:
        return jsonify({"error": "Authorization code not provided"}), 400
    
    try:
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        token_res = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10)
        token_json = token_res.json()
        
        if "error" in token_json:
            return jsonify({"error": "Token exchange failed", "details": token_json}), 400
        
        access_token = token_json.get("access_token")
        if not access_token:
            return jsonify({"error": "No access token received"}), 400
        
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        
        if user_res.status_code != 200:
            return jsonify({"error": "Failed to fetch user info"}), 400
            
        user_info = user_res.json()
        email = user_info.get("email", "").lower()
        
        if not email:
            return jsonify({"error": "No email found in Google response"}), 400
        
        if not user_info.get("verified_email", False):
            return jsonify({"error": "Email not verified with Google"}), 400
        
        is_admin = email in ADMIN_EMAILS
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        
        if not utilisateur:
            full_name = user_info.get("name", "")
            name_parts = full_name.split(' ', 1) if full_name else ["", ""]
            prenom = name_parts[0] if len(name_parts) > 0 else ""
            nom = name_parts[1] if len(name_parts) > 1 else ""
            
            utilisateur = Utilisateur(
                email=email,
                nom=nom,
                prenom=prenom,
                photo=user_info.get("picture"), 
                type_compte=TypeCompteEnum.admin if is_admin else TypeCompteEnum.user,
                mot_de_passe=None
            )
            db.session.add(utilisateur)
            db.session.commit()
        else:
            if user_info.get("picture") and utilisateur.photo != user_info.get("picture"):
                utilisateur.photo = user_info.get("picture")
            
            if is_admin and utilisateur.type_compte != TypeCompteEnum.admin:
                utilisateur.type_compte = TypeCompteEnum.admin
            
            db.session.commit()
        
        token_payload = {
            "user_id": utilisateur.id,
            "email": email,
            "name": user_info.get("name", ""),
            "prenom": utilisateur.prenom,
            "nom": utilisateur.nom,
            "picture": utilisateur.photo, 
            "type_compte": utilisateur.type_compte.value,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        }
        
        secret_key = current_app.config.get("SECRET_KEY")
        if not secret_key:
            return jsonify({"error": "Server configuration error"}), 500
            
        token = jwt.encode(token_payload, secret_key, algorithm="HS256")
        
        return jsonify({
            "token": token,
            "user": {
                "id": utilisateur.id,
                "email": email,
                "name": user_info.get("name", ""),
                "prenom": utilisateur.prenom,
                "nom": utilisateur.nom,
                "picture": utilisateur.photo, 
                "type_compte": utilisateur.type_compte.value
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Erreur API OAuth: {str(e)}")
        return jsonify({"error": "Unexpected error during OAuth"}), 500

@oauth_bp.route('/config', methods=['GET'])
def oauth_config():
    return jsonify({
        "google_client_configured": bool(GOOGLE_CLIENT_ID),
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "frontend_url": FRONTEND_URL,
        "admin_emails_count": len(ADMIN_EMAILS),
        "admin_emails": ADMIN_EMAILS if current_app.debug else "***hidden***"
    })



