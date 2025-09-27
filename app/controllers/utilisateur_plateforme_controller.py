# app/controllers/utilisateur_plateforme_controller.py
from flask import request, jsonify, url_for, redirect
from app.extensions import db
from app.models.plateforme import PlateformeConfig, UtilisateurPlateforme, OAuthState
from flask_jwt_extended import get_jwt_identity, decode_token
import secrets
import requests
import json
from datetime import datetime
import os


# =================================================================
# FONCTIONS UTILITAIRES INTERNES (OAuth)


def _construire_url_authorisation(plateforme, state):
    """Construit l'URL de redirection vers le fournisseur OAuth."""
    client_id = plateforme.get_client_id()
    scopes = plateforme.get_scopes()
    
    # CORRECTION 1: Utiliser le bon nom de blueprint
    redirect_uri = url_for("plateforme_bp.callback_oauth_route", plateforme_nom=plateforme.nom, _external=True)

    if plateforme.nom == "facebook":
        return (f"https://www.facebook.com/v12.0/dialog/oauth?"
                f"client_id={client_id}&redirect_uri={redirect_uri}&"
                f"scope={','.join(scopes)}&state={state}")
    elif plateforme.nom == "linkedin":
        return (f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&"
                f"scope={' '.join(scopes)}&state={state}")
    elif plateforme.nom == "google":
        return (f"https://accounts.google.com/o/oauth2/auth?"
                f"client_id={client_id}&redirect_uri={redirect_uri}&"
                f"scope={' '.join(scopes)}&response_type=code&state={state}")
    
    raise ValueError(f"Plateforme non supportée: {plateforme.nom}")


def _echanger_code_contre_token(plateforme_nom, code, oauth_state):
    """Échange le code d'autorisation contre un jeton d'accès."""
    plateforme = PlateformeConfig.query.get(oauth_state.plateforme_id)
    redirect_uri = url_for("plateforme_bp.callback_oauth_route", plateforme_nom=plateforme_nom, _external=True)

    try:
        if plateforme.nom == "facebook":
            response = requests.get("https://graph.facebook.com/v12.0/oauth/access_token", params={
                "client_id": plateforme.get_client_id(),
                "client_secret": plateforme.get_client_secret(),
                "redirect_uri": redirect_uri,
                "code": code
            }, timeout=30)
        elif plateforme.nom == "linkedin":
            response = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
                "client_id": plateforme.get_client_id(),
                "client_secret": plateforme.get_client_secret(),
                "redirect_uri": redirect_uri,
                "code": code,
                "grant_type": "authorization_code"
            }, timeout=30)
        elif plateforme.nom == "google":
            response = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": plateforme.get_client_id(),
                "client_secret": plateforme.get_client_secret(),
                "redirect_uri": redirect_uri,
                "code": code,
                "grant_type": "authorization_code"
            }, timeout=30)
        else:
            raise ValueError(f"Plateforme non supportée: {plateforme_nom}")
        
        # CORRECTION 2: Meilleure gestion des erreurs
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erreur lors de l'échange de token: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Erreur de requête lors de l'échange de token: {e}")
        return None


def _recuperer_infos_profil(plateforme_nom, access_token):
    """Récupère les informations de profil de l'utilisateur sur la plateforme externe."""
    try:
        if plateforme_nom == "facebook":
            response = requests.get(
                "https://graph.facebook.com/me",
                params={"access_token": access_token, "fields": "id,name,email"},
                timeout=30
            )
        elif plateforme_nom == "linkedin":
            response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30
            )
        elif plateforme_nom == "google":
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30
            )
        else:
            return None
            
        return response.json() if response.status_code == 200 else None
        
    except requests.RequestException as e:
        print(f"Erreur lors de la récupération du profil: {e}")
        return None


# =================================================================
# FONCTIONS PUBLIQUES DU CONTRÔLEUR

def get_user_plateformes():
    """CORRECTION 3: Renommage pour cohérence avec les routes"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Non authentifié"}), 401

    try:
        connexions = UtilisateurPlateforme.query.filter_by(utilisateur_id=utilisateur_id).all()
        return jsonify([c.to_dict() for c in connexions]), 200
    except Exception as e:
        print(f"Erreur lors de la récupération des plateformes: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


def disconnect_plateforme(plateforme_id):
    """CORRECTION 4: Utiliser l'ID au lieu du nom pour la déconnexion"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Non authentifié"}), 401

    try:
        # Utiliser l'ID de plateforme directement
        connexion = UtilisateurPlateforme.query.filter_by(
            utilisateur_id=utilisateur_id,
            plateforme_id=plateforme_id
        ).first()
        
        if not connexion:
            return jsonify({"error": "Connexion non trouvée"}), 404
            
        db.session.delete(connexion)
        db.session.commit()
        return jsonify({"message": "Déconnexion réussie"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la déconnexion: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


def initier_connexion_oauth(plateforme_nom):
    """CORRECTION 5: Retourner une redirection HTTP au lieu de JSON"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Utilisateur non authentifié"}), 401

    # Récupérer la plateforme active par son nom
    plateforme = PlateformeConfig.get_platform_by_name(plateforme_nom) 
    if not plateforme:
        return jsonify({"error": f"Plateforme {plateforme_nom} non trouvée"}), 404

    if not plateforme.is_active:
        return jsonify({"error": f"Plateforme {plateforme_nom} désactivée"}), 400

    try:
        # Vérifier si l'utilisateur est déjà connecté à cette plateforme
        connexion_existante = UtilisateurPlateforme.query.filter_by(
            utilisateur_id=utilisateur_id,
            plateforme_id=plateforme.id
        ).first()
        
        if connexion_existante and connexion_existante.is_token_valid():
            return jsonify({"message": "Déjà connecté à cette plateforme"}), 200

        # Générer un état OAuth sécurisé
        state = secrets.token_urlsafe(32)
        oauth_state = OAuthState(
            state=state, 
            utilisateur_id=utilisateur_id, 
            plateforme_id=plateforme.id
        )
        db.session.add(oauth_state)
        db.session.commit()

        auth_url = _construire_url_authorisation(plateforme, state)
        
        # CORRECTION MAJEURE: Rediriger directement vers le fournisseur OAuth
        return redirect(auth_url)
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'initiation OAuth: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


def callback_oauth(plateforme_nom):
    """CORRECTION 6: Rediriger vers le frontend avec des paramètres appropriés"""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    # URL du frontend - à configurer selon votre environnement
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    dashboard_url = f"{frontend_url}/dashboard"

    if error:
        error_message = request.args.get("error_description", error)
        return redirect(f"{dashboard_url}?oauth_error={error}&error_description={error_message}")

    if not code or not state:
        return redirect(f"{dashboard_url}?oauth_error=missing_parameters")

    oauth_state = OAuthState.query.filter_by(state=state).first()
    if not oauth_state:
        return redirect(f"{dashboard_url}?oauth_error=invalid_state")
        
    if not oauth_state.is_valid():
        return redirect(f"{dashboard_url}?oauth_error=expired_state")

    try:
        # Marquer l'état comme utilisé
        oauth_state.mark_as_used()
        db.session.commit()

        # Échanger le code contre un token
        token_data = _echanger_code_contre_token(plateforme_nom, code, oauth_state)
        if not token_data or "access_token" not in token_data:
            return redirect(f"{dashboard_url}?oauth_error=token_exchange_failed")

        # Chercher ou créer la connexion utilisateur
        connexion = UtilisateurPlateforme.query.filter_by(
            utilisateur_id=oauth_state.utilisateur_id,
            plateforme_id=oauth_state.plateforme_id
        ).first()
        
        if not connexion:
            connexion = UtilisateurPlateforme(
                utilisateur_id=oauth_state.utilisateur_id,
                plateforme_id=oauth_state.plateforme_id
            )
            db.session.add(connexion)

        # Mettre à jour le token
        connexion.update_token(
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token")  # Si disponible
        )

        # Récupérer les informations de profil
        profil_data = _recuperer_infos_profil(plateforme_nom, token_data["access_token"])
        if profil_data:
            connexion.meta = profil_data
            connexion.external_id = profil_data.get("id")
            
        # Activer la connexion
        connexion.is_active = True

        db.session.commit()
        
        # CORRECTION MAJEURE: Redirection vers le frontend avec succès
        return redirect(f"{dashboard_url}?oauth_success={plateforme_nom}")

    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors du callback OAuth: {e}")
        return redirect(f"{dashboard_url}?oauth_error=server_error")


# =================================================================
# FONCTIONS UTILITAIRES SUPPLÉMENTAIRES
# =================================================================

def refresh_token_if_needed(connexion):
    """Fonction utilitaire pour rafraîchir le token si nécessaire"""
    if not connexion.is_token_valid() and connexion.refresh_token:
        # Implémenter la logique de rafraîchissement selon la plateforme
        pass
    
def get_plateforme_status_util(utilisateur_id):
    """Obtenir le statut de toutes les plateformes pour un utilisateur"""
    plateformes_config = PlateformeConfig.query.filter_by(is_active=True).all()
    connexions = UtilisateurPlateforme.query.filter_by(utilisateur_id=utilisateur_id).all()
    
    connexions_dict = {c.plateforme_id: c for c in connexions}
    
    result = []
    for plateforme in plateformes_config:
        connexion = connexions_dict.get(plateforme.id)
        result.append({
            'plateforme_id': plateforme.id,
            'plateforme_nom': plateforme.nom,
            'is_connected': connexion is not None,
            'is_active': connexion.is_active if connexion else False,
            'token_valid': connexion.is_token_valid() if connexion else False
        })
    
    return result


def get_plateforme_status():
    """Obtenir le statut de toutes les plateformes pour l'utilisateur connecté"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Non authentifié"}), 401
    
    try:
        status = get_plateforme_status_util(utilisateur_id)  # Fonction utilitaire déjà définie
        return jsonify(status), 200
    except Exception as e:
        print(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


def refresh_plateforme_token(plateforme_id):
    """Rafraîchir le token d'une plateforme spécifique"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Non authentifié"}), 401
    
    try:
        connexion = UtilisateurPlateforme.query.filter_by(
            utilisateur_id=utilisateur_id,
            plateforme_id=plateforme_id
        ).first()
        
        if not connexion:
            return jsonify({"error": "Connexion non trouvée"}), 404
            
        if not connexion.refresh_token:
            return jsonify({"error": "Token de rafraîchissement non disponible"}), 400
        
        # Tentative de rafraîchissement
        success = refresh_token_if_needed(connexion)
        
        if success:
            db.session.commit()
            return jsonify({
                "message": "Token rafraîchi avec succès",
                "data": connexion.to_dict()
            }), 200
        else:
            return jsonify({"error": "Échec du rafraîchissement"}), 400
            
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors du rafraîchissement: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500