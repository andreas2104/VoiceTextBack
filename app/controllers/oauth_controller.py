from flask import Blueprint, redirect, request, jsonify, current_app, make_response
import requests
import jwt
import datetime
from datetime import timezone, timedelta
import os
from urllib.parse import urlencode, quote, quote_plus
from app.extensions import db
from app.models.utilisateur import Utilisateur, TypeCompteEnum
import secrets
import base64
import hashlib
from app.services.token_service import store_token
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies
)

# Créer UN SEUL Blueprint
oauth_bp = Blueprint('oauth_bp', __name__, url_prefix='/api/oauth')

# ============== CONFIGURATION ==============
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/oauth/google/callback")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# X/Twitter OAuth
X_CLIENT_ID = os.getenv('X_CLIENT_ID')
X_CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI", "http://localhost:5000/api/oauth/x/callback")
X_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
X_USERINFO_URL = "https://api.twitter.com/2/users/me"


ADMIN_EMAILS = []
admin_emails_env = os.getenv("ADMIN_EMAILS", "")
if admin_emails_env:
    ADMIN_EMAILS = [email.strip().lower() for email in admin_emails_env.split(',') if email.strip()]

oauth_states = {}

def cleanup_expired_states():

    import time
    current_time = time.time()
    expired = [k for k, v in oauth_states.items() 
               if current_time - v.get('timestamp', 0) > 600]
    for key in expired:
        oauth_states.pop(key, None)

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

def google_callback():
    """Callback Google OAuth avec cookies HttpOnly"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    frontend_success_url = f"{FRONTEND_URL}/dashboard"
    frontend_error_url = f"{FRONTEND_URL}/login"
    
    if error:
        error_url = f"{frontend_error_url}?error={quote_plus(error)}&provider=google"
        return redirect(error_url)
    
    if not code:
        error_url = f"{frontend_error_url}?error=no_code&provider=google"
        return redirect(error_url)
    
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
            error_url = f"{frontend_error_url}?error=token_exchange_failed&provider=google"
            return redirect(error_url)
        
        access_token = token_json.get("access_token")
        if not access_token:
            error_url = f"{frontend_error_url}?error=no_access_token&provider=google"
            return redirect(error_url)
        
        # eto no maka information utilisateur miaraka @token
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        
        if user_res.status_code != 200:
            error_url = f"{frontend_error_url}?error=user_info_failed&provider=google"
            return redirect(error_url)
            
        user_info = user_res.json()
        email = user_info.get("email", "").lower()
        
        if not email:
            error_url = f"{frontend_error_url}?error=no_email&provider=google"
            return redirect(error_url)
        
        if not user_info.get("verified_email", False):
            error_url = f"{frontend_error_url}?error=email_not_verified&provider=google"
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
                    photo=user_info.get("picture"),
                    type_compte=TypeCompteEnum.admin if is_admin else TypeCompteEnum.user,
                    mot_de_passe=None,
                    actif=True
                )
                
                db.session.add(utilisateur)
                db.session.commit()
                
                if is_admin:
                    current_app.logger.info(f"Nouveau compte admin créé pour: {email}")
                    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erreur création utilisateur {email}: {str(e)}")
                error_url = f"{frontend_error_url}?error=database_error&provider=google"
                return redirect(error_url)
        else:
            try:
                if user_info.get("picture") and utilisateur.photo != user_info.get("picture"):
                    utilisateur.photo = user_info.get("picture")
                
                if is_admin and utilisateur.type_compte != TypeCompteEnum.admin:
                    utilisateur.type_compte = TypeCompteEnum.admin
                    current_app.logger.info(f"Utilisateur {email} promu admin")
                
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erreur mise à jour utilisateur {email}: {str(e)}")
        try: 
               # stockage token dans db------------------------
            store_token (
                utilisateur_id= utilisateur.id,
                provider='google',
                access_token=token_json.get('access_token'),
                refresh_token=token_json.get('refresh_token'),
                expires_in=token_json.get('expires_in', 3600),
            )
            current_app.logger.info(f"Token Google stocker pour l'utilisateur {utilisateur.id}")
        except Exception as e:
            current_app.logger.error(f"Erreur stockage token Google: {str(e)}")
                # jusq ici---------------    

                # manamboatra token eto 
        access_token_jwt = create_access_token(
            identity=utilisateur.id,
            additional_claims={
                'email': utilisateur.email,
                'type_compte': utilisateur.type_compte.value
            }
        )
        refresh_token_jwt = create_refresh_token(identity=utilisateur.id)
        response = redirect(frontend_success_url)
        set_access_cookies(response, access_token_jwt)
        set_refresh_cookies(response, refresh_token_jwt)
        current_app.logger.info(f"Cookies JWT définis pour {utilisateur.email}")
        return response
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur réseau OAuth: {str(e)}")
        error_url = f"{frontend_error_url}?error=network_error&provider=google"
        return redirect(error_url)
    except Exception as e:
        current_app.logger.error(f"Erreur inattendue OAuth: {str(e)}")
        error_url = f"{frontend_error_url}?error=unexpected_error&provider=google"
        return redirect(error_url)


def login_x():
    """Initier la connexion X/Twitter OAuth"""
    if not X_CLIENT_ID or not X_CLIENT_SECRET:
        return redirect(f"{FRONTEND_URL}/login?error=x_not_configured")
    
    try:
       
        cleanup_expired_states()
           
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(43)

        import time
        oauth_states[state] = {
            'verifier': code_verifier,
            'timestamp': time.time()
        }
        
        current_app.logger.info(f"[X OAuth] State créé: {state[:10]}... (total states: {len(oauth_states)})")
        
        params = {
            'response_type': 'code',
            'client_id': X_CLIENT_ID,
            'redirect_uri': X_REDIRECT_URI,
            'scope': 'tweet.read tweet.write users.read offline.access',
            'state': state,
            'code_challenge': code_verifier,
            'code_challenge_method': 'plain'
        }
        
        auth_url = f"{X_AUTH_URL}?{urlencode(params)}"
        return redirect(auth_url)
        
    except Exception as e:
        current_app.logger.error(f"Erreur login X: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(f"{FRONTEND_URL}/login?error=x_init_failed")


def x_callback():
    """Callback X/Twitter OAuth avec cookies HttpOnly"""
    code = request.args.get('code')
    received_state = request.args.get('state')
    error = request.args.get('error')
    
    frontend_success_url = f"{FRONTEND_URL}/dashboard"
    frontend_error_url = f"{FRONTEND_URL}/login"
    
    current_app.logger.info(f"[X Callback] Reçu - Code: {'présent' if code else 'absent'}, State: {received_state[:10] if received_state else 'None'}...")
    
    if error:
        current_app.logger.error(f"Erreur OAuth X: {error}")
        return redirect(f"{frontend_error_url}?error=auth_denied&provider=x")
    
    if not code:
        return redirect(f"{frontend_error_url}?error=no_code&provider=x")
    
    if not received_state:
        return redirect(f"{frontend_error_url}?error=no_state&provider=x")
    
    # Vérification du state
    state_data = oauth_states.get(received_state)
    
    if not state_data:
        current_app.logger.error(f"State introuvable: {received_state[:10]}...")
        return redirect(f"{frontend_error_url}?error=invalid_state&provider=x")
    
    code_verifier = state_data['verifier']
    oauth_states.pop(received_state, None)
    
    current_app.logger.info(f"[X Callback] State validé et supprimé")
    
    try:
        # Échange du code contre un token
        token_data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": X_CLIENT_ID,
            "redirect_uri": X_REDIRECT_URI,
            "code_verifier": code_verifier
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        current_app.logger.info("[X Callback] Échange du code contre un token...")
        token_res = requests.post(
            X_TOKEN_URL,
            data=token_data,
            headers=headers,
            auth=(X_CLIENT_ID, X_CLIENT_SECRET),
            timeout=10
        )
        
        token_json = token_res.json()
        
        if "error" in token_json or token_res.status_code != 200:
            current_app.logger.error(f"Erreur token X (status {token_res.status_code}): {token_json}")
            return redirect(f"{frontend_error_url}?error=token_exchange_failed&provider=x")
        
        access_token = token_json.get("access_token")
        if not access_token:
            return redirect(f"{frontend_error_url}?error=no_access_token&provider=x")
        
        current_app.logger.info("[X Callback] Token obtenu, récupération des infos utilisateur...")
        
        # Récupération des infos utilisateur
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"user.fields": "id,name,username,profile_image_url"}
        
        user_res = requests.get(
            X_USERINFO_URL,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if user_res.status_code == 429:
            current_app.logger.error("Rate limit X atteint")
            return redirect(f"{frontend_error_url}?error=rate_limit_exceeded&provider=x")
        
        user_info = user_res.json()
        
        if "data" not in user_info:
            current_app.logger.error(f"Erreur user info X (status {user_res.status_code}): {user_info}")
            return redirect(f"{frontend_error_url}?error=user_info_failed&provider=x")
        
        twitter_user = user_info["data"]
        twitter_id = twitter_user.get("id")
        username = twitter_user.get("username")
        name = twitter_user.get("name", username)
        
        current_app.logger.info(f"[X Callback] Utilisateur X: @{username} (ID: {twitter_id})")
        
        # Gestion de l'utilisateur
        email = f"x_{twitter_id}@twitter.oauth"
        
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if not utilisateur:
            utilisateur = Utilisateur(
                email=email,
                nom=name,
                prenom="",
                mot_de_passe=None,
                type_compte=TypeCompteEnum.user,
                actif=True
            )
            db.session.add(utilisateur)
            db.session.commit()
            current_app.logger.info(f"Nouvel utilisateur X créé: {username}")
        else:
            if utilisateur.nom != name:
                utilisateur.nom = name
                db.session.commit()
            current_app.logger.info(f"Utilisateur X existant: {username}")
        
        # Stockage du token
        try:
            store_token(
                utilisateur_id=utilisateur.id,
                provider='x',
                access_token=token_json.get('access_token'),
                refresh_token=token_json.get('refresh_token'),
                expires_in=token_json.get('expires_in', 3600),
            )
            current_app.logger.info(f"Token X stocké pour l'utilisateur {utilisateur.id}")
        except Exception as e:
            current_app.logger.error(f"Erreur stockage token X: {str(e)}")
            # On continue même si le stockage du token échoue
        
        # Création des tokens JWT
        access_token_jwt = create_access_token(
            identity=utilisateur.id,
            additional_claims={
                'email': utilisateur.email,
                'type_compte': utilisateur.type_compte.value,
                'username': username,
                'x_access_token': access_token
            }
        )
        refresh_token_jwt = create_refresh_token(identity=utilisateur.id)
        
        # Préparation de la réponse
        response = redirect(frontend_success_url)
        
        set_access_cookies(response, access_token_jwt)
        set_refresh_cookies(response, refresh_token_jwt)
        
        current_app.logger.info(f"=== CALLBACK X RÉUSSI ===")
        current_app.logger.info(f"Utilisateur: @{username} - Redirection vers dashboard")
        current_app.logger.info(f"Cookies JWT définis pour @{username}")
        
        return response
        
    except requests.exceptions.Timeout:
        current_app.logger.error("Timeout X OAuth")
        return redirect(f"{frontend_error_url}?error=timeout&provider=x")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur inattendue X OAuth: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(f"{frontend_error_url}?error=server_error&provider=x")

def oauth_logout():
    """Déconnexion OAuth - supprime les cookies HttpOnly"""
    try:
        response = jsonify({"message": "Déconnexion OAuth réussie"})
        unset_jwt_cookies(response)
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Erreur déconnexion OAuth: {str(e)}")
        return jsonify({"error": "Erreur lors de la déconnexion"}), 500



def x_debug():
    """Vérifier la configuration X OAuth"""
    return jsonify({
        "configured": bool(X_CLIENT_ID and X_CLIENT_SECRET),
        "client_id_present": bool(X_CLIENT_ID),
        "client_id_length": len(X_CLIENT_ID) if X_CLIENT_ID else 0,
        "redirect_uri": X_REDIRECT_URI,
        "active_states": len(oauth_states),
        "state_keys": list(oauth_states.keys())[:3] if oauth_states else []
    })