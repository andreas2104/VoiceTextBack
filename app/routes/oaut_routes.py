# oauth_routes.py - Version avec redirection vers frontend
from flask import Blueprint, redirect, request, jsonify, current_app
import requests
import jwt
import datetime
import os
from urllib.parse import urlencode, quote_plus

oauth_bp = Blueprint('oauth_bp', __name__)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/oauth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

@oauth_bp.route('/login/google', methods=['GET'])
def login_google():
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
    code = request.args.get('code')
    error = request.args.get('error')
    
    # Préparer l'URL de redirection vers le frontend
    frontend_callback_url = f"{FRONTEND_URL}/auth/google/callback"
    
    if error:
        error_url = f"{frontend_callback_url}?error={quote_plus(error)}"
        return redirect(error_url)
    
    if not code:
        error_url = f"{frontend_callback_url}?error=no_code"
        return redirect(error_url)
    
    try:
        # Échanger le code contre un token
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
            error_url = f"{frontend_callback_url}?error={quote_plus('token_exchange_failed')}"
            return redirect(error_url)
        
        access_token = token_json.get("access_token")
        if not access_token:
            error_url = f"{frontend_callback_url}?error=no_access_token"
            return redirect(error_url)
        
        # Récupérer les informations utilisateur
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        
        if user_res.status_code != 200:
            error_url = f"{frontend_callback_url}?error=user_info_failed"
            return redirect(error_url)
            
        user_info = user_res.json()
        email = user_info.get("email")
        
        if not email:
            error_url = f"{frontend_callback_url}?error=no_email"
            return redirect(error_url)
        
        if not user_info.get("verified_email", False):
            error_url = f"{frontend_callback_url}?error=email_not_verified"
            return redirect(error_url)
        
        # Gérer l'utilisateur en base de données
        # from models import Utilisateur, db
        # utilisateur = Utilisateur.query.filter_by(email=email).first()
        # if not utilisateur:
        #     utilisateur = Utilisateur(
        #         email=email, 
        #         nom=user_info.get("name", ""),
        #         photo=user_info.get("picture", ""),
        #         type_compte=TypeCompteEnum.utilisateur
        #     )
        #     db.session.add(utilisateur)
        #     db.session.commit()
        
        # Générer un JWT
        token_payload = {
            "email": email,
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
            "iat": datetime.datetime.now(datetime.UTC),
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
        }
        
        secret_key = current_app.config.get("SECRET_KEY")
        if not secret_key:
            error_url = f"{frontend_callback_url}?error=server_config_error"
            return redirect(error_url)
            
        token = jwt.encode(token_payload, secret_key, algorithm="HS256")
        
        # Rediriger vers le frontend avec le token
        success_url = f"{frontend_callback_url}?token={token}"
        return redirect(success_url)
        
    except requests.exceptions.RequestException:
        error_url = f"{frontend_callback_url}?error=network_error"
        return redirect(error_url)
    except jwt.InvalidTokenError:
        error_url = f"{frontend_callback_url}?error=jwt_error"
        return redirect(error_url)
    except Exception:
        error_url = f"{frontend_callback_url}?error=unexpected_error"
        return redirect(error_url)

# Alternative : endpoint API pour le callback si vous préférez JSON
@oauth_bp.route('/google/callback/api', methods=['GET'])
def google_callback_api():
    """Version API qui retourne JSON au lieu de rediriger"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return jsonify({"error": f"Google OAuth error: {error}"}), 400
    
    if not code:
        return jsonify({"error": "Authorization code not provided"}), 400
    
    try:
        # ... (même logique que google_callback)
        # Mais retourner JSON au lieu de rediriger
        
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
            return jsonify({"error": "Failed to fetch token", "details": token_json}), 400
        
        access_token = token_json.get("access_token")
        if not access_token:
            return jsonify({"error": "No access token received"}), 400
        
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        
        if user_res.status_code != 200:
            return jsonify({"error": "Failed to fetch user info"}), 400
            
        user_info = user_res.json()
        email = user_info.get("email")
        
        if not email:
            return jsonify({"error": "No email found in Google response"}), 400
        
        if not user_info.get("verified_email", False):
            return jsonify({"error": "Email not verified with Google"}), 400
        
        token_payload = {
            "email": email,
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
            "iat": datetime.datetime.now(datetime.UTC),
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
        }
        
        secret_key = current_app.config.get("SECRET_KEY")
        if not secret_key:
            return jsonify({"error": "Server configuration error"}), 500
            
        token = jwt.encode(token_payload, secret_key, algorithm="HS256")
        
        return jsonify({
            "token": token, 
            "user": {
                "email": email,
                "name": user_info.get("name", ""),
                "picture": user_info.get("picture", "")
            }
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Network error during OAuth process"}), 500
    except Exception as e:
        return jsonify({"error": "Unexpected error during OAuth"}), 500