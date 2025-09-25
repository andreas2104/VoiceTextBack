from flask import request, jsonify, url_for
from app.extensions import db
from app.models.plateforme import PlateformeConfig, UtilisateurPlateforme, OAuthState
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
import secrets
import requests
import json


def create_plateforme():
    """Création d’une plateforme (admin uniquement)"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Aucune donnée reçue"}), 400

        nom = data.get("nom")
        config = data.get("config", {})
        active = data.get("active", True)

        if not nom or not config.get("client_id") or not config.get("client_secret"):
            return jsonify({"error": "Champs requis manquants: nom, client_id, client_secret"}), 400

        # Vérifier doublon
        if PlateformeConfig.query.filter_by(nom=nom).first():
            return jsonify({"error": f"La plateforme {nom} existe déjà"}), 400

        plateforme = PlateformeConfig(
            nom=nom,
            config=config,
            active=active
        )
        db.session.add(plateforme)
        db.session.commit()

        return jsonify({
            "message": f"Plateforme {nom} créée avec succès",
            "id": plateforme.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def get_plateformes():
    """Lister toutes les plateformes actives"""
    try:
        plateformes = PlateformeConfig.get_active_platforms()
        return jsonify([p.to_dict() for p in plateformes]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_plateforme_by_id(plateforme_id):
    """Récupérer une plateforme par ID"""
    plateforme = PlateformeConfig.query.get(plateforme_id)
    if not plateforme:
        return jsonify({"error": "Plateforme introuvable"}), 404

    return jsonify(plateforme.to_dict()), 200


def update_plateforme(plateforme_id):
    """Mise à jour d’une plateforme (admin uniquement)"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized"}), 403

    plateforme = PlateformeConfig.query.get(plateforme_id)
    if not plateforme:
        return jsonify({"error": "Plateforme introuvable"}), 404

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Aucune donnée reçue"}), 400

        plateforme.nom = data.get("nom", plateforme.nom)
        config = data.get("config")
        if config:
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except json.JSONDecodeError:
                    return jsonify({"error": "Format JSON invalide pour config"}), 400
            plateforme.config = config

        plateforme.active = data.get("active", plateforme.active)
        plateforme.date_modification = datetime.utcnow()

        db.session.commit()
        return jsonify({"message": "Plateforme mise à jour avec succès"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def delete_plateforme(plateforme_id):
    """Suppression d’une plateforme (admin uniquement)"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized"}), 403

    plateforme = PlateformeConfig.query.get(plateforme_id)
    if not plateforme:
        return jsonify({"error": "Plateforme introuvable"}), 404

    try:
        db.session.delete(plateforme)
        db.session.commit()
        return jsonify({"message": "Plateforme supprimée avec succès"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# utilisateurplateform controler

def get_connexions_utilisateur():
    """Lister toutes les connexions d’un utilisateur"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Non authentifié"}), 401

    try:
        connexions = UtilisateurPlateforme.query.filter_by(utilisateur_id=utilisateur_id).all()
        return jsonify([c.to_dict() for c in connexions]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def deconnexion_plateforme(plateforme_nom):
    """Déconnecter un utilisateur d’une plateforme"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Non authentifié"}), 401

    try:
        connexion = UtilisateurPlateforme.get_user_platform(utilisateur_id, plateforme_nom)
        if connexion:
            db.session.delete(connexion)
            db.session.commit()
        return jsonify({"message": f"Déconnexion {plateforme_nom} réussie"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

# oauthplateformecontroller

def initier_connexion_oauth(plateforme_nom):
    """Initier le processus OAuth"""
    utilisateur_id = get_jwt_identity()
    if not utilisateur_id:
        return jsonify({"error": "Utilisateur non authentifié"}), 401

    plateforme = PlateformeConfig.get_platform_by_name(plateforme_nom)
    if not plateforme:
        return jsonify({"error": f"Plateforme {plateforme_nom} non trouvée"}), 404

    try:
        state = secrets.token_urlsafe(32)
        oauth_state = OAuthState(state=state, utilisateur_id=utilisateur_id, plateforme_id=plateforme.id)
        db.session.add(oauth_state)
        db.session.commit()

        auth_url = _construire_url_authorisation(plateforme, state)

        return jsonify({"auth_url": auth_url, "state": state}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def _construire_url_authorisation(plateforme, state):
    client_id = plateforme.get_client_id()
    scopes = plateforme.get_scopes()
    redirect_uri = url_for("plateforme_bp.callback_oauth", plateforme_nom=plateforme.nom, _external=True)

    if plateforme.nom == "facebook":
        return (f"https://www.facebook.com/v12.0/dialog/oauth?"
                f"client_id={client_id}&redirect_uri={redirect_uri}&"
                f"scope={','.join(scopes)}&state={state}")
    elif plateforme.nom == "linkedin":
        return (f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&"
                f"scope={' '.join(scopes)}&state={state}")
    raise ValueError(f"Plateforme non supportée: {plateforme.nom}")


def callback_oauth(plateforme_nom):
    """Callback après OAuth (récupérer token + créer connexion utilisateur)"""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return jsonify({"error": f"Erreur d’autorisation: {error}"}), 400

    oauth_state = OAuthState.query.filter_by(state=state).first()
    if not oauth_state or not oauth_state.is_valid():
        return jsonify({"error": "État OAuth invalide ou expiré"}), 400

    try:
        oauth_state.mark_as_used()
        db.session.commit()

        token_data = _echanger_code_contre_token(plateforme_nom, code, oauth_state)
        if not token_data or "access_token" not in token_data:
            return jsonify({"error": "Échec échange token"}), 400

        connexion = UtilisateurPlateforme.get_user_platform(oauth_state.utilisateur_id, plateforme_nom)
        if not connexion:
            connexion = UtilisateurPlateforme(
                utilisateur_id=oauth_state.utilisateur_id,
                plateforme_id=oauth_state.plateforme_id
            )
            db.session.add(connexion)

        connexion.update_token(
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in")
        )

        profil_data = _recuperer_infos_profil(plateforme_nom, token_data["access_token"])
        if profil_data:
            connexion.meta = profil_data
            connexion.external_id = profil_data.get("id")

        db.session.commit()
        return jsonify({"message": f"Connexion réussie à {plateforme_nom}", "data": connexion.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def _echanger_code_contre_token(plateforme_nom, code, oauth_state):
    plateforme = PlateformeConfig.query.get(oauth_state.plateforme_id)
    redirect_uri = url_for("plateforme_bp.callback_oauth", plateforme_nom=plateforme_nom, _external=True)

    if plateforme.nom == "facebook":
        response = requests.get("https://graph.facebook.com/v12.0/oauth/access_token", params={
            "client_id": plateforme.get_client_id(),
            "client_secret": plateforme.get_client_secret(),
            "redirect_uri": redirect_uri,
            "code": code
        })
    elif plateforme.nom == "linkedin":
        response = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "client_id": plateforme.get_client_id(),
            "client_secret": plateforme.get_client_secret(),
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code"
        })
    else:
        raise ValueError(f"Plateforme non supportée: {plateforme_nom}")

    return response.json() if response.status_code == 200 else None


def _recuperer_infos_profil(plateforme_nom, access_token):
    try:
        if plateforme_nom == "facebook":
            response = requests.get(
                "https://graph.facebook.com/me",
                params={"access_token": access_token, "fields": "id,name,email"}
            )
        elif plateforme_nom == "linkedin":
            response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
        else:
            return None
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None