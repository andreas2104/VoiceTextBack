from flask import Blueprint, redirect, request, jsonify, current_app, session
import requests
import jwt
import datetime
from datetime import timezone  
import os
from urllib.parse import urlencode, quote_plus
from app.extensions import db
from app.models.utilisateur import Utilisateur, TypeCompteEnum
import hashlib
import secrets
import base64
from datetime import datetime as dt, timedelta, timezone as datetime_timezone
from datetime import timezone as datetime_UTC
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps

oauth_bp = Blueprint('oauth_bp', __name__, url_prefix='/api/oauth')

# ============== GOOGLE OAUTH ==============

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/oauth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

ADMIN_EMAILS = []
admin_emails_env = os.getenv("ADMIN_EMAILS", "")
if admin_emails_env:
    ADMIN_EMAILS = [email.strip().lower() for email in admin_emails_env.split(',') if email.strip()]

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
    """Callback Google OAuth avec création/mise à jour utilisateur"""
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
                    photo=user_info.get("picture"),
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
                if user_info.get("picture") and utilisateur.photo != user_info.get("picture"):
                    utilisateur.photo = user_info.get("picture")
                
                if is_admin and utilisateur.type_compte != TypeCompteEnum.admin:
                    utilisateur.type_compte = TypeCompteEnum.admin
                    current_app.logger.info(f"Utilisateur {email} promu admin")
                
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erreur mise à jour utilisateur {email}: {str(e)}")
                error_url = f"{frontend_callback_url}?error=database_error"
                return redirect(error_url)
        
        token_payload = {
            "user_id": utilisateur.id,
            "email": email,
            "name": user_info.get("name", ""),
            "prenom": utilisateur.prenom,
            "nom": utilisateur.nom,
            "picture": utilisateur.photo, 
            "type_compte": utilisateur.type_compte.value,
            "iat": dt.utcnow(),
            "exp": dt.utcnow() + timedelta(hours=24),
        }
        
        secret_key = current_app.config.get("SECRET_KEY")
        if not secret_key:
            error_url = f"{frontend_callback_url}?error=server_config_error"
            return redirect(error_url)
            
        token = jwt.encode(token_payload, secret_key, algorithm="HS256")
        
        success_url = f"{frontend_callback_url}?token={token}"
        current_app.logger.info(f"=== CALLBACK GOOGLE RÉUSSI ===")
        current_app.logger.info(f"Utilisateur: {email}")
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

# ============== X (TWITTER) OAUTH ==============

X_CLIENT_ID = os.getenv('X_CLIENT_ID')
X_CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI", "http://localhost:5000/api/oauth/x/callback")

X_AUTH_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_USERINFO_URL = "https://api.x.com/2/users/me"

X_SCOPES = "tweet.read users.read tweet.write offline.access"

# def generate_pkce_pair():
#     """Génère un code_verifier et code_challenge sécurisés (S256)"""
#     verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
#     challenge_bytes = hashlib.sha256(verifier.encode('utf-8')).digest()
#     challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
#     return verifier, challenge

# @oauth_bp.route('/login/x', methods=['GET'])
# def login_x():
#     """Initier la connexion X OAuth"""
#     if not X_CLIENT_ID or not X_CLIENT_SECRET:
#         return jsonify({"error": "X OAuth not configured properly"}), 500
    
#     state = secrets.token_urlsafe(32)
#     verifier, challenge = generate_pkce_pair()
    
#     # ✅ STOCKAGE DE SESSION - CORRIGÉ
#     try:
#         session.permanent = True  # ✅ REND LA SESSION PERSISTANTE
#         session['oauth_state'] = state
#         session['oauth_verifier'] = verifier
#         session['oauth_provider'] = 'x'
#         session['oauth_timestamp'] = dt.utcnow().isoformat()
#         session.modified = True  # ✅ FORCE L'ÉCRITURE DE SESSION
        
#         current_app.logger.info(f"=== LOGIN X INITIÉ ===")
#         current_app.logger.info(f"State stocké: {state}")
#         current_app.logger.info(f"Session initialisée avec succès")
#         current_app.logger.info(f"Session ID: {request.cookies.get('session', 'N/A')[:20]}")
        
#     except Exception as e:
#         current_app.logger.error(f"Erreur session: {str(e)}")
#         return jsonify({"error": "Session error", "details": str(e)}), 500
    
#     auth_url = (
#         f"{X_AUTH_URL}?"
#         f"response_type=code&"
#         f"client_id={X_CLIENT_ID}&"
#         f"redirect_uri={quote_plus(X_REDIRECT_URI)}&"
#         f"scope={quote_plus(X_SCOPES)}&"
#         f"state={state}&"
#         f"code_challenge={challenge}&"
#         f"code_challenge_method=S256"
#     )
    
#     current_app.logger.info(f"Redirection vers X...")
#     return redirect(auth_url)

# @oauth_bp.route('/x/callback', methods=['GET'])
# def callback_x():
#     """Callback X OAuth - VERSION CORRIGÉE"""
#     code = request.args.get('code')
#     state = request.args.get('state')
#     error = request.args.get('error')
    
#     frontend_callback_url = f"{FRONTEND_URL}/authXCallback"
    
#     current_app.logger.info(f"=== X CALLBACK REÇU ===")
#     current_app.logger.info(f"Code: {code[:20] if code else 'None'}...")
#     current_app.logger.info(f"State reçu: {state}")
#     current_app.logger.info(f"Session ID reçue: {request.cookies.get('session', 'N/A')[:20]}")
#     current_app.logger.info(f"Session keys: {list(session.keys())}")
    
#     if error:
#         current_app.logger.error(f"Erreur X reçue: {error}")
#         error_url = f"{frontend_callback_url}?error={quote_plus(error)}"
#         return redirect(error_url)
    
#     if not code:
#         current_app.logger.error(f"Code manquant")
#         error_url = f"{frontend_callback_url}?error=no_code"
#         return redirect(error_url)
    
#     # ✅ RÉCUPÉRATION DE LA SESSION
#     stored_state = session.get('oauth_state')
#     verifier = session.get('oauth_verifier')
    
#     current_app.logger.info(f"State reçu: {state}")
#     current_app.logger.info(f"State stocké: {stored_state}")
#     current_app.logger.info(f"Verifier présent: {bool(verifier)}")
    
#     # ✅ VALIDATION RENFORCÉE
#     if not stored_state:
#         current_app.logger.error(f"État stocké manquant - session perdue")
#         error_url = f"{frontend_callback_url}?error=session_expired"
#         return redirect(error_url)
    
#     if state != stored_state:
#         current_app.logger.error(f"State mismatch: reçu={state}, stocké={stored_state}")
#         error_url = f"{frontend_callback_url}?error=invalid_state"
#         return redirect(error_url)
    
#     if not verifier:
#         current_app.logger.error(f"PKCE verifier manquant")
#         error_url = f"{frontend_callback_url}?error=pkce_error"
#         return redirect(error_url)

#     try:
#         # Échange du code contre un token
#         token_data = {
#             "code": code,
#             "grant_type": "authorization_code",
#             "client_id": X_CLIENT_ID,
#             "redirect_uri": X_REDIRECT_URI,
#             "code_verifier": verifier
#         }
        
#         current_app.logger.info(f"Échange du token avec X...")
#         token_res = requests.post(
#             X_TOKEN_URL, 
#             data=token_data, 
#             auth=(X_CLIENT_ID, X_CLIENT_SECRET),
#             headers={'Content-Type': 'application/x-www-form-urlencoded'}
#         )
        
#         if token_res.status_code != 200:
#             current_app.logger.error(f"Token exchange failed: {token_res.status_code} - {token_res.text}")
#             error_url = f"{frontend_callback_url}?error=token_exchange_failed"
#             return redirect(error_url)
            
#         token_json = token_res.json()
#         access_token = token_json.get("access_token")
        
#         if not access_token:
#             current_app.logger.error(f"Pas de access token dans la réponse")
#             error_url = f"{frontend_callback_url}?error=no_access_token"
#             return redirect(error_url)

#         # Récupération des infos utilisateur
#         current_app.logger.info(f"Récupération des infos utilisateur...")
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json"
#         }
        
#         user_res = requests.get(
#             f"{X_USERINFO_URL}?user.fields=id,name,username,profile_image_url",
#             headers=headers
#         )
        
#         if user_res.status_code != 200:
#             current_app.logger.error(f"User info fetch failed: {user_res.status_code} - {user_res.text}")
#             error_url = f"{frontend_callback_url}?error=user_info_failed"
#             return redirect(error_url)
        
#         user_info = user_res.json()
#         user_data = user_info.get("data", {})
#         twitter_id = user_data.get("id")
#         name = user_data.get("name")
#         username = user_data.get("username")

#         if not twitter_id:
#             current_app.logger.error(f"Pas d'ID utilisateur")
#             error_url = f"{frontend_callback_url}?error=no_user_id"
#             return redirect(error_url)

#         # Création/mise à jour de l'utilisateur
#         email = f"{username}@x.com"
        
#         try:
#             utilisateur = Utilisateur.query.filter_by(email=email).first()
#             if not utilisateur:
#                 utilisateur = Utilisateur(
#                     email=email,
#                     nom=name or username,
#                     prenom="",
#                     mot_de_passe="",
#                     type_compte=TypeCompteEnum.user,
#                     actif=True
#                 )
#                 db.session.add(utilisateur)
#                 db.session.commit()
#                 current_app.logger.info(f"Nouvel utilisateur X créé: {email}")
#             else:
#                 if name and utilisateur.nom != name:
#                     utilisateur.nom = name
#                     db.session.commit()

#         except Exception as e:
#             db.session.rollback()
#             current_app.logger.error(f"Erreur DB: {str(e)}")
#             error_url = f"{frontend_callback_url}?error=database_error"
#             return redirect(error_url)

#         # Génération du token JWT
#         token_payload = {
#             "user_id": utilisateur.id,
#             "email": email,
#             "name": name or username,
#             "type_compte": utilisateur.type_compte.value,
#             "iat": dt.utcnow(),
#             "exp": dt.utcnow() + timedelta(hours=24),
#         }
        
#         secret_key = current_app.config.get("SECRET_KEY")
#         if not secret_key:
#             error_url = f"{frontend_callback_url}?error=server_config_error"
#             return redirect(error_url)
        
#         app_token = jwt.encode(token_payload, secret_key, algorithm="HS256")
        
#         # ✅ NETTOYAGE DE SESSION
#         session.pop('oauth_state', None)
#         session.pop('oauth_verifier', None)
#         session.pop('oauth_provider', None)
#         session.pop('oauth_timestamp', None)
#         session.modified = True
        
#         success_url = f"{frontend_callback_url}?token={app_token}"
#         current_app.logger.info(f"=== CALLBACK X RÉUSSI ===")
#         current_app.logger.info(f"Utilisateur: {email}")
#         return redirect(success_url)

#     except requests.exceptions.RequestException as e:
#         current_app.logger.error(f"Erreur réseau: {str(e)}")
#         error_url = f"{frontend_callback_url}?error=network_error"
#         return redirect(error_url)
#     except Exception as e:
#         current_app.logger.error(f"Erreur inattendue: {str(e)}")
#         error_url = f"{frontend_callback_url}?error=unexpected_error"
#         return redirect(error_url)

@oauth_bp.route('/login/x', methods=['GET'])
def login_x():
    """Étape 1 : redirige l'utilisateur vers la page d'autorisation Twitter"""
    auth_url = (
        f"{X_AUTH_URL}?response_type=code"
        f"&client_id={X_CLIENT_ID}"
        f"&redirect_uri={X_REDIRECT_URI}"
        f"&scope=tweet.read%20users.read%20offline.access"
        f"&state=random_string_123"
        f"&code_challenge=challenge"
        f"&code_challenge_method=plain"
    )
    return redirect(auth_url)


@oauth_bp.route('/x/callback', methods=['GET'])
def x_callback():
    """Étape 2 : callback Twitter → échange code contre token"""
    code = request.args.get('code')
    if not code:
        # Rediriger vers le frontend avec une erreur
        return redirect(f"{FRONTEND_URL}/authXCallback?error=no_code")

    token_data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": X_CLIENT_ID,
        "redirect_uri": X_REDIRECT_URI,
        "code_verifier": "challenge"
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post(X_TOKEN_URL, data=token_data, headers=headers, auth=(X_CLIENT_ID, X_CLIENT_SECRET))
    token_json = token_res.json()

    if "error" in token_json:
        return redirect(f"{FRONTEND_URL}/authXCallback?error=token_exchange_failed")

    access_token = token_json.get("access_token")
    if not access_token:
        return redirect(f"{FRONTEND_URL}/authXCallback?error=no_token")

    # Étape 3 : Récupérer les infos utilisateur
    headers = {"Authorization": f"Bearer {access_token}"}
    user_res = requests.get(X_USERINFO_URL, headers=headers)
    user_info = user_res.json()

    if "data" not in user_info:
        return redirect(f"{FRONTEND_URL}/authXCallback?error=user_info_failed")

    twitter_user = user_info["data"]
    twitter_id = twitter_user.get("id")
    username = twitter_user.get("username")

    email = f"{username}@twitter.com"

    # Étape 4 : Vérifie ou crée l'utilisateur en base
    utilisateur = Utilisateur.query.filter_by(email=email).first()
    if not utilisateur:
        utilisateur = Utilisateur(
            email=email,
            nom=username,
            prenom="",
            mot_de_passe="",
            type_compte=TypeCompteEnum.user,
            actif=True
        )
        db.session.add(utilisateur)
        db.session.commit()

    # Étape 5 : Générer un JWT
    token_payload = {
        "email": email,
        "user_id": utilisateur.id, 
        "name": username,
        "type_compte": utilisateur.type_compte.value,
        "exp": datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1),
    }
    token = jwt.encode(token_payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    return redirect(f"{FRONTEND_URL}/authXCallback?token={token}")


@oauth_bp.route('/x/publish', methods=['POST'])
def x_publish():
    """
    Publier un tweet automatiquement depuis ton app
    Corps JSON attendu :
    {
      "user_id": 123,
      "text": "Mon tweet auto depuis mon app 🚀"
    }
    """
    data = request.get_json()
    user_id = data.get("user_id")
    text = data.get("text")

    if not user_id or not text:
        return jsonify({"error": "user_id et text sont requis"}), 400

    utilisateur = Utilisateur.query.get(user_id)
    if not utilisateur or not utilisateur.access_token:
        return jsonify({"error": "Utilisateur ou access_token introuvable"}), 404

    headers = {
        "Authorization": f"Bearer {utilisateur.access_token}",
        "Content-Type": "application/json"
    }

    tweet_data = {"text": text}
    response = requests.post(X_TWEET_URL, json=tweet_data, headers=headers)
    result = response.json()

    if response.status_code != 201 and "data" not in result:
        return jsonify({"error": "Échec de la publication", "details": result}), 400

    return jsonify({"message": "Tweet publié avec succès ✅", "tweet": result}), 201