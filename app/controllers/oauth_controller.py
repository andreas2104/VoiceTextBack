from flask import Blueprint, redirect, request, jsonify, current_app
import requests
import jwt
import datetime
import os

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
  from models import Utilisateur,TypeCompteEnum 
  from app.extensions import db

  utilisateur = Utilisateur.query.filter_by(email=email).first()
  if not utilisateur:
        utilisateur = Utilisateur(    
          email = email
          nom = user_info.get('given_name',''),
          prenom = user_info.get('family_name',''),
          mot_de_passe = ""
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
  