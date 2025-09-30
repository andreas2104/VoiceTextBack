from flask import request, jsonify, url_for, redirect
from app.extensions import db
from app.models.plateforme import PlateformeConfig, UtilisateurPlateforme, OAuthState
from app.models.utilisateur import Utilisateur
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
import secrets
import requests


def get_user_plateformes():
    """Récupère toutes les plateformes connectées de l'utilisateur actuel"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        user_plateformes = UtilisateurPlateforme.query.filter_by(
            utilisateur_id=current_user_id
        ).all()
        
        return jsonify([up.to_dict() for up in user_plateformes]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_user_plateforme_by_id(user_plateforme_id):
    """Récupère une connexion plateforme spécifique"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        user_plateforme = UtilisateurPlateforme.query.filter_by(
            id=user_plateforme_id,
            utilisateur_id=current_user_id
        ).first()

        if not user_plateforme:
            return jsonify({"error": "Connexion plateforme introuvable"}), 404

        return jsonify(user_plateforme.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def disconnect_user_plateforme(user_plateforme_id):
    """Déconnecte un utilisateur d'une plateforme"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        user_plateforme = UtilisateurPlateforme.query.filter_by(
            id=user_plateforme_id,
            utilisateur_id=current_user_id
        ).first()

        if not user_plateforme:
            return jsonify({"error": "Connexion plateforme introuvable"}), 404

        plateforme_nom = user_plateforme.plateforme.nom if user_plateforme.plateforme else "inconnue"
        
        db.session.delete(user_plateforme)
        db.session.commit()

        return jsonify({
            "message": f"Déconnecté de {plateforme_nom} avec succès"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def update_user_plateforme_meta(user_plateforme_id):
    """Met à jour les métadonnées d'une connexion plateforme"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        data = request.get_json()
        if not data or 'meta' not in data:
            return jsonify({"error": "Champ 'meta' requis"}), 400

        user_plateforme = UtilisateurPlateforme.query.filter_by(
            id=user_plateforme_id,
            utilisateur_id=current_user_id
        ).first()

        if not user_plateforme:
            return jsonify({"error": "Connexion plateforme introuvable"}), 404

        user_plateforme.meta.update(data['meta'])
        user_plateforme.updated_at = datetime.utcnow()
        
        db.session.commit()

        return jsonify({
            "message": "Métadonnées mises à jour avec succès",
            "data": user_plateforme.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



def initiate_oauth(plateforme_nom):
    """Initialise le flux OAuth pour une plateforme"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        # Récupérer la configuration de la plateforme
        plateforme = PlateformeConfig.get_platform_by_name(plateforme_nom)
        if not plateforme:
            return jsonify({"error": f"Plateforme {plateforme_nom} introuvable ou inactive"}), 404

        # Générer un state unique
        state = secrets.token_urlsafe(32)

        # Créer l'enregistrement OAuth state
        oauth_state = OAuthState(
            state=state,
            utilisateur_id=current_user_id,
            plateforme_id=plateforme.id
        )
        db.session.add(oauth_state)
        db.session.commit()

        # Construire l'URL d'autorisation
        client_id = plateforme.get_client_id()
        scopes = plateforme.get_scopes()
        redirect_uri = url_for('oauth_callback', plateforme_nom=plateforme_nom, _external=True)
        
        # URL d'autorisation (à adapter selon la plateforme)
        auth_url = plateforme.config.get('auth_url')
        if not auth_url:
            return jsonify({"error": "URL d'autorisation non configurée"}), 500

        auth_params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'response_type': 'code',
            'scope': ' '.join(scopes) if scopes else ''
        }

        # Construire l'URL complète
        from urllib.parse import urlencode
        full_auth_url = f"{auth_url}?{urlencode(auth_params)}"

        return jsonify({
            "auth_url": full_auth_url,
            "state": state
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def oauth_callback(plateforme_nom):
    """Gère le callback OAuth"""
    try:
        # Récupérer les paramètres
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        if error:
            return jsonify({
                "error": f"Erreur OAuth: {error}",
                "description": request.args.get('error_description', '')
            }), 400

        if not code or not state:
            return jsonify({"error": "Paramètres manquants"}), 400

        # Vérifier le state
        oauth_state = OAuthState.query.filter_by(state=state).first()
        if not oauth_state or not oauth_state.is_valid():
            return jsonify({"error": "State invalide ou expiré"}), 400

        if oauth_state.used:
            return jsonify({"error": "State déjà utilisé"}), 400

        # Marquer le state comme utilisé
        oauth_state.mark_as_used()
        db.session.commit()

        # Récupérer la plateforme
        plateforme = PlateformeConfig.query.get(oauth_state.plateforme_id)
        if not plateforme or plateforme.nom != plateforme_nom:
            return jsonify({"error": "Plateforme invalide"}), 400

        # Échanger le code contre un token
        token_url = plateforme.config.get('token_url')
        if not token_url:
            return jsonify({"error": "URL de token non configurée"}), 500

        redirect_uri = url_for('oauth_callback', plateforme_nom=plateforme_nom, _external=True)
        
        token_data = {
            'client_id': plateforme.get_client_id(),
            'client_secret': plateforme.get_client_secret(),
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            return jsonify({
                "error": "Échec de l'échange de token",
                "details": token_response.text
            }), 500

        token_json = token_response.json()
        access_token = token_json.get('access_token')
        expires_in = token_json.get('expires_in')
        refresh_token = token_json.get('refresh_token')

        if not access_token:
            return jsonify({"error": "Token d'accès non reçu"}), 500

        # Récupérer les informations de l'utilisateur depuis la plateforme
        user_info_url = plateforme.config.get('user_info_url')
        external_id = None
        
        if user_info_url:
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(user_info_url, headers=headers)
            
            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                external_id = user_info.get('id') or user_info.get('sub')

        # Créer ou mettre à jour la connexion utilisateur-plateforme
        user_plateforme = UtilisateurPlateforme.get_user_platform(
            oauth_state.utilisateur_id,
            plateforme_nom
        )

        if user_plateforme:
            # Mettre à jour le token existant
            user_plateforme.update_token(access_token, expires_in=expires_in)
            if external_id:
                user_plateforme.external_id = external_id
            if refresh_token:
                user_plateforme.meta['refresh_token'] = refresh_token
        else:
            # Créer une nouvelle connexion
            user_plateforme = UtilisateurPlateforme(
                utilisateur_id=oauth_state.utilisateur_id,
                plateforme_id=plateforme.id,
                external_id=external_id,
                access_token=access_token,
                meta={'refresh_token': refresh_token} if refresh_token else {}
            )
            user_plateforme.update_token(access_token, expires_in=expires_in)
            db.session.add(user_plateforme)

        db.session.commit()

        return jsonify({
            "message": f"Connexion à {plateforme_nom} réussie",
            "data": user_plateforme.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def refresh_token(user_plateforme_id):
    """Rafraîchit le token d'accès d'une connexion plateforme"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        user_plateforme = UtilisateurPlateforme.query.filter_by(
            id=user_plateforme_id,
            utilisateur_id=current_user_id
        ).first()

        if not user_plateforme:
            return jsonify({"error": "Connexion plateforme introuvable"}), 404

        refresh_token = user_plateforme.meta.get('refresh_token')
        if not refresh_token:
            return jsonify({"error": "Aucun refresh token disponible"}), 400

        plateforme = user_plateforme.plateforme
        token_url = plateforme.config.get('token_url')
        
        if not token_url:
            return jsonify({"error": "URL de token non configurée"}), 500

        token_data = {
            'client_id': plateforme.get_client_id(),
            'client_secret': plateforme.get_client_secret(),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            return jsonify({
                "error": "Échec du rafraîchissement du token",
                "details": token_response.text
            }), 500

        token_json = token_response.json()
        new_access_token = token_json.get('access_token')
        expires_in = token_json.get('expires_in')
        new_refresh_token = token_json.get('refresh_token')

        if not new_access_token:
            return jsonify({"error": "Nouveau token d'accès non reçu"}), 500

        # Mettre à jour le token
        user_plateforme.update_token(new_access_token, expires_in=expires_in)
        if new_refresh_token:
            user_plateforme.meta['refresh_token'] = new_refresh_token

        db.session.commit()

        return jsonify({
            "message": "Token rafraîchi avec succès",
            "data": user_plateforme.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def check_token_validity(user_plateforme_id):
    """Vérifie la validité du token d'une connexion plateforme"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        user_plateforme = UtilisateurPlateforme.query.filter_by(
            id=user_plateforme_id,
            utilisateur_id=current_user_id
        ).first()

        if not user_plateforme:
            return jsonify({"error": "Connexion plateforme introuvable"}), 404

        is_valid = user_plateforme.is_token_valid()

        return jsonify({
            "valid": is_valid,
            "expires_at": user_plateforme.token_expires_at.isoformat() if user_plateforme.token_expires_at else None,
            "plateforme": user_plateforme.plateforme.nom if user_plateforme.plateforme else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




def cleanup_expired_states():
    """Nettoie les states OAuth expirés (fonction admin)"""
    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401

    current_user = Utilisateur.query.get(current_user_id)
    if not current_user or current_user.type_compte.value != 'admin':
        return jsonify({"error": "Accès admin requis"}), 403

    try:
        # Supprimer les states expirés ou utilisés de plus de 24h
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        expired_states = OAuthState.query.filter(
            (OAuthState.used == True) | (OAuthState.created_at < cutoff_time)
        ).all()

        count = len(expired_states)
        
        for state in expired_states:
            db.session.delete(state)
        
        db.session.commit()

        return jsonify({
            "message": f"{count} states OAuth nettoyés",
            "count": count
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500