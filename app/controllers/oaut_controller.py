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
    # from models import Utilisateur, db
    # utilisateur = Utilisateur.query.filter_by(email=email).first()
    # if not utilisateur:
    #     utilisateur = Utilisateur(email=email, mot_de_passe="", type_compte=TypeCompteEnum.utilisateur)
    #     db.session.add(utilisateur)
    #     db.session.commit()

    # Générer un JWT de ton backend
  token_payload = {
        "email": email,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    }
  token = jwt.encode(token_payload, current_app.config["SECRET_KEY"], algorithm="HS256")

  return jsonify({"token": token, "user": user_info}), 200
  

  # pour facebook

from flask import request, jsonify, redirect, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

from app.extensions import db
from app.models.plateforme import Plateforme, TypePlateformeEnum, StatutConnexionEnum
from app.services.facebook_oauth_service import FacebookOAuthService

class OAuthController:
    
    @staticmethod
    @jwt_required()
    def initier_connexion_facebook():
        """Initie la connexion OAuth Facebook"""
        try:
            # Générer l'URL d'autorisation
            auth_url = FacebookOAuthService.get_authorization_url()
            
            return jsonify({
                'success': True,
                'auth_url': auth_url,
                'message': 'Redirections vers Facebook pour autorisation'
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @staticmethod
    @jwt_required()
    def callback_facebook():
        """Traite le callback OAuth Facebook"""
        try:
            current_user_id = get_jwt_identity()
            
            # Récupérer le code d'autorisation
            code = request.args.get('code')
            error = request.args.get('error')
            
            if error:
                return jsonify({
                    'success': False,
                    'error': f'Facebook authorization error: {error}'
                }), 400
            
            if not code:
                return jsonify({
                    'success': False,
                    'error': 'Authorization code not received'
                }), 400
            
            # Étape 1: Échanger le code contre un token
            token_result = FacebookOAuthService.exchange_code_for_token(code)
            if not token_result['success']:
                return jsonify({
                    'success': False,
                    'error': token_result['error']
                }), 400
            
            short_token = token_result['access_token']
            
            # Étape 2: Obtenir un token longue durée
            long_token_result = FacebookOAuthService.get_long_lived_token(short_token)
            if not long_token_result['success']:
                return jsonify({
                    'success': False,
                    'error': long_token_result['error']
                }), 400
            
            long_lived_token = long_token_result['access_token']
            expires_in = long_token_result['expires_in']
            
            # Étape 3: Récupérer les pages de l'utilisateur
            pages_result = FacebookOAuthService.get_user_pages(long_lived_token)
            if not pages_result['success']:
                return jsonify({
                    'success': False,
                    'error': pages_result['error']
                }), 400
            
            pages = pages_result['pages']
            
            if not pages:
                return jsonify({
                    'success': False,
                    'error': 'Aucune page Facebook trouvée ou permissions insuffisantes'
                }), 400
            
            # Étape 4: Sauvegarder les plateformes
            connected_pages = []
            for page in pages:
                # Chercher si la page existe déjà
                existing_platform = Plateforme.query.filter_by(
                    id_utilisateur=current_user_id,
                    nom_plateforme=TypePlateformeEnum.FACEBOOK,
                    id_compte_externe=page['id']
                ).first()
                
                if existing_platform:
                    # Mettre à jour
                    existing_platform.access_token = page['access_token']
                    existing_platform.nom_compte = page['name']
                    existing_platform.token_expiration = datetime.utcnow() + timedelta(seconds=expires_in)
                    existing_platform.statut_connexion = StatutConnexionEnum.CONNECTE
                    existing_platform.actif = True
                    existing_platform.date_modification = datetime.utcnow()
                    platform = existing_platform
                else:
                    # Créer nouvelle plateforme
                    platform = Plateforme(
                        id_utilisateur=current_user_id,
                        nom_plateforme=TypePlateformeEnum.FACEBOOK,
                        nom_compte=page['name'],
                        id_compte_externe=page['id'],
                        access_token=page['access_token'],
                        token_expiration=datetime.utcnow() + timedelta(seconds=expires_in),
                        statut_connexion=StatutConnexionEnum.CONNECTE,
                        permissions_accordees=['pages_manage_posts', 'pages_read_engagement'],
                        limite_posts_jour=25
                    )
                    db.session.add(platform)
                
                connected_pages.append(platform.to_dict())
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'{len(connected_pages)} page(s) Facebook connectée(s)',
                'data': connected_pages
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @staticmethod
    @jwt_required()
    def lister_pages_facebook():
        """Liste les pages Facebook disponibles (pour re-sélection)"""
        try:
            current_user_id = get_jwt_identity()
            
            # Récupérer une plateforme Facebook existante pour le token
            platform = Plateforme.query.filter_by(
                id_utilisateur=current_user_id,
                nom_plateforme=TypePlateformeEnum.FACEBOOK,
                statut_connexion=StatutConnexionEnum.CONNECTE
            ).first()
            
            if not platform or not platform.is_token_valid():
                return jsonify({
                    'success': False,
                    'error': 'Aucune connexion Facebook valide trouvée. Veuillez vous reconnecter.'
                }), 400
            
            # Utiliser le token de l'utilisateur (pas de page) pour lister les pages
            pages_result = FacebookOAuthService.get_user_pages(platform.access_token)
            
            if not pages_result['success']:
                return jsonify({
                    'success': False,
                    'error': pages_result['error']
                }), 400
            
            return jsonify({
                'success': True,
                'data': pages_result['pages']
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500