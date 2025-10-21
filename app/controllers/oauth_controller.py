from urllib.parse import urlencode, quote_plus
import os
from flask import Blueprint, redirect, request, jsonify, current_app, session
from models import Utilisateur,TypeCompteEnum 
from app.extensions import db
import requests
import jwt
import datetime
import os
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone as datetime_timezone
from datetime import timezone as datetime_UTC
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps


oauth_bp = Blueprint('oauth_bp', __name__)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/oauth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@oauth_bp.route('/login/google', methods=['GET'])
def login_google():

  auth_url = (
    f"{GOOGLE_AUTH_URL}?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
        f"&prompt=consent"
  )
  return redirect(auth_url)

@oauth_bp.route('/login/google/callback', methods=['GET'])
def google_callback():
  code = request.args.get('code')
  if not code:
    return jsonify({"error": "Authorization code not provided"}), 400
  token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
  token_res = requests.post(GOOGLE_TOKEN_URL, data=token_data)
  token_json = token_res.json()

  if "error" in token_json:
        return jsonify({"error": "Failed to fetch token", "details": token_json}), 400

  access_token = token_json["access_token"]

    # Récupérer les infos utilisateur depuis Google
  headers = {"Authorization": f"Bearer {access_token}"}
  user_res = requests.get(GOOGLE_USERINFO_URL, headers=headers)
  user_info = user_res.json()

    # Exemple de données : { "id": "...", "email": "...", "verified_email": true, "name": "...", "picture": "..." }
  email = user_info.get("email")

  if not email:
      return jsonify({"error": "No email found in Google response"}), 400

    # ⚡ ICI : soit tu crées l'utilisateur en DB s'il n'existe pas, soit tu le récupères


  utilisateur = Utilisateur.query.filter_by(email=email).first()
  if not utilisateur:
        utilisateur = Utilisateur(    
          email = email,
          nom = user_info.get('given_name',''),
          prenom = user_info.get('family_name',''),
          mot_de_passe = "",
          type_compte = TypeCompteEnum.user,
          actif=True
        )
        # utilisateur = Utilisateur(email=email, mot_de_passe="", type_compte=TypeCompteEnum.utilisateur)
        db.session.add(utilisateur)
        db.session.commit()

    # Générer un JWT de ton backend
  token_payload = {
        "email": email,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    }
  token = jwt.encode(token_payload, current_app.config["SECRET_KEY"], algorithm="HS256")

  return jsonify({"token": token, "user": user_info}), 200
  

X_CLIENT_ID = os.getenv('X_CLIENT_ID')
X_CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI", "http://localhost:5000/api/oauth/x/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")  # Ajout : définissez en env

X_AUTH_URL = "https://x.com/i/oauth2/authorize"  # Corrigé
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"  # Corrigé : /2/ et x.com
X_USERINFO_URL = "https://api.x.com/2/users/me"  # Corrigé : x.com

X_SCOPES = "tweet.read users.read tweet.write offline.access"

def generate_pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    challenge_bytes = hashlib.sha256(verifier.encode('utf-8')).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    return verifier, challenge

@oauth_bp.route('/login/x', methods=['GET'])
def login_x():
    """Initier la connexion X OAuth avec PKCE"""
    if not X_CLIENT_ID or not X_CLIENT_SECRET:
        return jsonify({"error": "X OAuth not configured properly"}), 500
    
    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    session['oauth_state'] = state
    session['oauth_verifier'] = verifier
    
    params = {
        "response_type": "code",
        "client_id": X_CLIENT_ID,
        "redirect_uri": X_REDIRECT_URI,
        "scope": X_SCOPES,  # Utilisez la var
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256"
    }
    auth_url = f"{X_AUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)

@oauth_bp.route('/x/callback', methods=['GET'])  # Note : /x/callback (pas /oauth/x pour matcher votre log)
def x_callback():
    """Callback X OAuth avec PKCE"""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    frontend_callback_url = f"{FRONTEND_URL}/login"  # Ajusté pour matcher votre redirect (ou /authXCallback si différent)
    
    if error:
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details={quote_plus(error)}")
    if not code:
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=no_code")
    
    # Vérification du state
    stored_state = session.get('oauth_state')
    verifier = session.get('oauth_verifier')
    if not stored_state or state != stored_state:
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=invalid_state")
    if not verifier:
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=pkce_error")
    
    try:
        # 1️⃣ Échanger le code contre un token (Basic Auth pour confidential client)
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": X_REDIRECT_URI,
            "code_verifier": verifier
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # CORRECTION : Utilisez auth= pour Basic Auth (client_id:client_secret en base64)
        token_res = requests.post(X_TOKEN_URL, data=token_data, headers=headers, auth=(X_CLIENT_ID, X_CLIENT_SECRET), timeout=10)
        token_json = token_res.json()
        
        current_app.logger.info(f"Token response: {token_json}")  # Log pour debug
        
        if token_res.status_code != 200 or "error" in token_json:
            return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=token_exchange_failed&response={quote_plus(str(token_json))}")
        
        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")  # Stockez si besoin (pour auto-refresh)
        if not access_token:
            return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=no_access_token")
        
        # 2️⃣ Récupérer infos utilisateur (avec check status)
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(X_USERINFO_URL, headers=headers, timeout=10)
        current_app.logger.info(f"User info response status: {user_res.status_code}, body: {user_res.text}")  # Log détaillé pour debug
        
        if user_res.status_code != 200:
            return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=user_info_http_{user_res.status_code}&response={quote_plus(user_res.text)}")
        
        user_info = user_res.json()
        if "data" not in user_info or not user_info["data"]:
            return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=user_info_failed&response={quote_plus(str(user_info))}")  # Ajout response pour debug
        
        twitter_user = user_info["data"]
        username = twitter_user.get("username")
        if not username:
            return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=no_username")
        
        email = f"{username}@x.com"  # Mise à jour (x.com)
        
        # 3️⃣ Vérifier ou créer l'utilisateur (ajoutez refresh_token si vous avez un champ DB)
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if not utilisateur:
            utilisateur = Utilisateur(
                email=email,
                nom=username,
                prenom="",
                mot_de_passe=None,
                type_compte=TypeCompteEnum.user,
                actif=True
            )
            db.session.add(utilisateur)
            db.session.commit()
        # Optionnel : utilisateur.x_refresh_token = refresh_token ; db.session.commit()
        
        # 4️⃣ Générer un JWT (exp 24h comme vous)
        payload = {
            "user_id": utilisateur.id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        secret = current_app.config["SECRET_KEY"]
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Nettoyer la session
        session.pop('oauth_state', None)
        session.pop('oauth_verifier', None)
        
        # 5️⃣ Rediriger vers le front avec succès
        success_url = f"{frontend_callback_url}?token={quote_plus(token)}&provider=x"
        current_app.logger.info(f"✅ OAuth X réussi pour {email}")
        return redirect(success_url)
    
    except requests.exceptions.Timeout:
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=timeout")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur requête X: {str(e)}")
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=request_error")
    except Exception as e:
        current_app.logger.error(f"Erreur callback X: {str(e)}")
        return redirect(f"{frontend_callback_url}?error=x_auth_failed&details=unexpected_error")
# @oauth_bp.route('/login/x/callback', methods=['GET'])
# def callback_x():
#     code = request.args.get('code')
#     state = request.args.get('state')
#     from flask import session
#     stored_state = session.get('oauth_state')
#     if not code or state != stored_state:
#         return jsonify({"error": "Invalid state or code"}), 400

#     verifier = session.get('oauth_verifier')
#     if not verifier:
#         return jsonify({"error": "PKCE verifier missing"}), 400

#     # Échange du code contre token (Basic Auth pour confidential client)
#     token_data = {
#         "code": code,
#         "grant_type": "authorization_code",
#         "client_id": X_CLIENT_ID,
#         "redirect_uri": X_REDIRECT_URI,
#         "code_verifier": verifier
#     }
#     token_res = requests.post(X_TOKEN_URL, data=token_data, auth=(X_CLIENT_ID, X_CLIENT_SECRET))
#     token_json = token_res.json()

#     if token_res.status_code != 200 or "error" in token_json:
#         return jsonify({"error": "Failed to get token", "details": token_json}), 400

#     access_token = token_json.get("access_token")
#     refresh_token = token_json.get("refresh_token")  # Important pour auto-post !

#     # Récupération des infos utilisateur
#     headers = {"Authorization": f"Bearer {access_token}"}
#     user_res = requests.get(X_USERINFO_URL, headers=headers)
#     if user_res.status_code != 200:
#         return jsonify({"error": "Failed to fetch user info"}), 400
#     user_info = user_res.json()

#     twitter_id = user_info.get("data", {}).get("id")
#     name = user_info.get("data", {}).get("name")
#     username = user_info.get("data", {}).get("username")

#     if not twitter_id:
#         return jsonify({"error": "No user ID"}), 400

#     # Gestion utilisateur (ajout des tokens X)
#     email = f"{username}@x.com"  # Hack ; pour vrai email, ajoutez 'users.email' aux scopes (si autorisé)
#     utilisateur = Utilisateur.query.filter_by(email=email).first()
#     if not utilisateur:
#         utilisateur = Utilisateur(
#             email=email,
#             nom=name or "",
#             prenom="",
#             mot_de_passe="",  # Pas de MDP pour OAuth
#             type_compte=TypeCompteEnum.user,
#             actif=True
#         )
#         db.session.add(utilisateur)
#         db.session.commit()
#     else:
#         # Update si existant
#         utilisateur.nom = name or utilisateur.nom

#     # Stockez les tokens X
#     utilisateur.x_access_token = access_token
#     utilisateur.x_refresh_token = refresh_token
#     db.session.commit()

#     # JWT pour votre app (exp 1h)
#     token_payload = {
#         "email": email,
#         "exp": datetime.now(UTC) + timedelta(hours=1),
#     }
#     app_token = jwt.encode(token_payload, current_app.config["SECRET_KEY"], algorithm="HS256")

#     # Nettoyez session
#     session.pop('oauth_state', None)
#     session.pop('oauth_verifier', None)

#     return jsonify({"token": app_token, "user": user_info}), 200

# Helper pour rafraîchir le token (utilisé avant post)
def refresh_x_token(utilisateur):
    if not utilisateur.x_refresh_token:
        raise ValueError("No refresh token")
    
    token_data = {
        "refresh_token": utilisateur.x_refresh_token,
        "grant_type": "refresh_token",
        "client_id": X_CLIENT_ID,
    }
    token_res = requests.post(X_TOKEN_URL, data=token_data, auth=(X_CLIENT_ID, X_CLIENT_SECRET))
    token_json = token_res.json()
    
    if token_res.status_code != 200 or "error" in token_json:
        raise ValueError(f"Refresh failed: {token_json}")
    
    # Update DB
    utilisateur.x_access_token = token_json.get("access_token")
    if "refresh_token" in token_json:  # Nouveau refresh si fourni
        utilisateur.x_refresh_token = token_json["refresh_token"]
    db.session.commit()
    return utilisateur.x_access_token

# Décorateur pour routes protégées (ex. : /post)
def jwt_required_x(func):
    @wraps(func)
    @jwt_required()  # De flask-jwt-extended
    def wrapper(*args, **kwargs):
        email = get_jwt_identity()
        user = Utilisateur.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "User not found"}), 401
        request.user = user  # Attache user à request
        return func(*args, **kwargs)
    return wrapper

# Nouvel endpoint pour poster (ex. : après génération de contenu)
@oauth_bp.route('/post', methods=['POST'])
@jwt_required_x  # Protégé par votre JWT
def post_to_x():
    user = request.user  # De l'utilisateur connecté
    data = request.json
    text = data.get('text', '')  # Le contenu généré
    media_ids = data.get('media_ids', [])  # Optionnel : IDs d'images/vidéos uploadées avant

    if not text:
        return jsonify({"error": "Text required"}), 400

    access_token = user.x_access_token
    if not access_token:
        return jsonify({"error": "No X access token"}), 401

    # Payload pour tweet
    payload = {"text": text}
    if media_ids:
        payload["media"] = {"media_ids": media_ids}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Tentative de post ; si 401 (expired), refresh et retry
    res = requests.post("https://api.x.com/2/tweets", json=payload, headers=headers)
    if res.status_code == 401:  # Unauthorized (token expired)
        try:
            access_token = refresh_x_token(user)
            headers["Authorization"] = f"Bearer {access_token}"
            res = requests.post("https://api.x.com/2/tweets", json=payload, headers=headers)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401
    
    if res.status_code != 201:
        return jsonify({"error": "Post failed", "details": res.json()}), res.status_code

    tweet_data = res.json().get("data", {})
    return jsonify({"success": True, "tweet_id": tweet_data.get("id"), "text": tweet_data.get("text")}), 201