from flask import request, jsonify, redirect, current_app, url_for
# Mise à jour des imports pour inclure Utilisateur et TypeCompteEnum
from app.models.utilisateur import Utilisateur,TypeCompteEnum 
from app.models.plateforme import PlateformeConfig, UtilisateurPlateforme, OAuthState
from app.extensions import db
from flask_jwt_extended import get_jwt_identity
import secrets
import jwt
import datetime
import requests
import os
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError


def get_user_plateformes():
  """
  Récupère toutes les plateformes connectées pour l'utilisateur courant.
  (Adapté à votre structure d'erreur de requête originale)
  """
  try:
    current_user_id = get_jwt_identity()
    if not current_user_id:
      return jsonify({"error": "Utilisateur non authentifier"}), 401
    
    utilisateurs_plateformes = UtilisateurPlateforme.query.filter_by(
      utilisateur_id=current_user_id
    ).all()

    return jsonify([up.to_dict() for up in utilisateurs_plateformes]),200
  
  except Exception as e:
    print(f"Erreur lors de la recuperation des plateformes de l'utilisateur: {e}")
    return jsonify({"error": str(e)}), 500
  
def disconnect_platforme(plateforme_id):
    """
    Déconnecte une plateforme spécifique de l'utilisateur courant.
    (Nom de fonction adapté à votre requête)
    """
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
          return jsonify({"error": "Utilsateur non authentifie"}), 401

        connexion = UtilisateurPlateforme.query.filter_by(
           utilisateur_id=current_user_id,
           plateforme_id = plateforme_id
        ).first()

        if not connexion:
           return jsonify({"error": "Connexion a la plateforme non trouvee"}),404

        db.session.delete(connexion)
        db.session.commit()

        return jsonify({"messge":"plateforme deconnecte avec success"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la deconnexion de la plateforme: {e}")
        return jsonify({"error": str(e)}), 500
    
def start_oauth(plateforme_nom):
    """
    Démarre le processus OAuth en redirigeant l'utilisateur (initiate_oauth dans la version précédente).
    """
    try:
        current_user_id = get_jwt_identity()
        # Conversion du nom en minuscules pour la recherche et le mapping
        pl_nom_lower = plateforme_nom.lower()
        
        plateforme = PlateformeConfig.query.filter_by(nom=pl_nom_lower).first()

        if not current_user_id:
            return jsonify({"error": "Utilisateur non authentifie pour l'0auth"}), 401

        if not plateforme:
            return jsonify({"error": "Plateforme non trouve"}), 404

        state_token = secrets.token_urlsafe(32)
        
        # Sauvegarder l'état dans la base de données
        oauth_state = OAuthState(
            state=state_token,
            utilisateur_id=current_user_id,
            plateforme_id=plateforme.id
        )
        db.session.add(oauth_state)
        db.session.commit()
        
        # --- LOGIQUE DE MAPPING OAUTH ---
        config = plateforme.config
        oauth_url = None

        if pl_nom_lower == 'google':
            oauth_url = (
                f"{config.get('auth_url')}?response_type=code"
                f"&client_id={config.get('client_id')}"
                f"&redirect_uri={config.get('redirect_uri')}"
                f"&scope={'+'.join(config.get('scopes', []))}"
                f"&state={state_token}"
                f"&access_type=offline&prompt=consent"
            )
        elif pl_nom_lower == 'facebook':
            # Facebook utilise 'client_id', 'redirect_uri', 'state', et 'scope'
            oauth_url = (
                f"{config.get('auth_url')}?client_id={config.get('client_id')}"
                f"&redirect_uri={config.get('redirect_uri')}"
                f"&state={state_token}"
                f"&scope={','.join(config.get('scopes', []))}"
            )
        elif pl_nom_lower == 'linkedin':
            # LinkedIn utilise 'response_type=code', 'client_id', 'redirect_uri', 'state', et 'scope'
             oauth_url = (
                f"{config.get('auth_url')}?response_type=code"
                f"&client_id={config.get('client_id')}"
                f"&redirect_uri={config.get('redirect_uri')}"
                f"&state={state_token}"
                f"&scope={'%20'.join(config.get('scopes', []))}" # %20 pour espace
            )
        
        if oauth_url:
            return redirect(oauth_url)
        else:
            return jsonify({"error": "Plateforme non prise en charge pour l'OAuth"}), 400

    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'initiation de l'OAuth: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


def handle_oauth_callback(plateforme_nom):
    """
    Gère la redirection de la plateforme OAuth et le token d'échange.
    (La logique de cette fonction n'a pas besoin d'être renommée car elle est appelée par la route)
    """
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code or not state:
            return jsonify({"error": "Code ou état manquant"}), 400

        # Vérifier l'état dans la base de données
        oauth_state = OAuthState.query.filter_by(state=state).first()
        if not oauth_state or not oauth_state.is_valid():
            db.session.rollback()
            return jsonify({"error": "État invalide ou expiré"}), 400
        
        oauth_state.mark_as_used()
        db.session.commit()

        plateforme = oauth_state.plateforme
        pl_nom_lower = plateforme.nom.lower()
        config = plateforme.config
        
        # --- PRÉPARATION DE L'ÉCHANGE DE JETON ---
        token_data = {
            "code": code,
            "client_id": config.get("client_id"),
            "client_secret": config.get("client_secret"),
            "redirect_uri": config.get("redirect_uri"),
            "grant_type": "authorization_code",
        }
        
        # --- RÉCUPÉRATION ET VALIDATION DES JETONS ---
        token_res = requests.post(config.get("token_url"), data=token_data)
        token_json = token_res.json()

        if "error" in token_json:
            db.session.rollback()
            return jsonify({"error": f"Échec de l'échange de jeton ({pl_nom_lower})", "details": token_json}), 400

        access_token = token_json.get("access_token")
        
        # --- RÉCUPÉRATION DES INFOS UTILISATEUR ET ID EXTERNE ---
        headers = {"Authorization": f"Bearer {access_token}"}
        user_info = {}
        external_id = None
        
        if pl_nom_lower == 'google':
            user_res = requests.get(config.get("userinfo_url"), headers=headers)
            user_info = user_res.json()
            external_id = user_info.get("id")
            # Google utilise 'id'
            
        elif pl_nom_lower == 'facebook':
            # Facebook Graph API pour obtenir l'ID de l'utilisateur
            user_res = requests.get(
                f"{config.get('userinfo_url')}?fields=id,name,email&access_token={access_token}"
            )
            user_info = user_res.json()
            external_id = user_info.get("id")
            # Facebook utilise 'id'
            
        elif pl_nom_lower == 'linkedin':
            # LinkedIn utilise un endpoint spécifique pour les informations utilisateur
            user_res = requests.get(config.get("userinfo_url"), headers=headers)
            user_info = user_res.json()
            external_id = user_info.get("sub") # 'sub' est l'ID unique dans OpenID Connect
            # LinkedIn utilise 'sub' (subject)

        if not external_id:
            db.session.rollback()
            return jsonify({"error": f"ID externe manquant dans la réponse de {pl_nom_lower}"}), 400

        # --- SAUVEGARDE DE LA CONNEXION ---
        connexion = UtilisateurPlateforme.query.filter_by(
            utilisateur_id=oauth_state.utilisateur_id,
            plateforme_id=plateforme.id
        ).first()

        if not connexion:
            connexion = UtilisateurPlateforme(
                utilisateur_id=oauth_state.utilisateur_id,
                plateforme_id=plateforme.id,
                external_id=external_id,
                meta=user_info 
            )
            db.session.add(connexion)

        # Mettre à jour le jeton, même si l'utilisateur existe déjà
        connexion.update_token(
            access_token=access_token,
            expires_in=token_json.get('expires_in'),
        )
        db.session.commit()

        # Redirection vers le front-end avec un message de succès
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        return redirect(f"{frontend_url}/profile?status=success&platform={plateforme.nom}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors du traitement du callback OAuth: {e}")
        return jsonify({"error": str(e)}), 500
