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
        existing = PlateformeConfig.query.filter_by(nom=nom).first()
        if existing:
            existing.active = True
            existing.config = config
            db.session.commit()
            return jsonify({
                "message": f"plateforme {nom} réactivée",
                "id": existing.id
            }), 200
        # if PlateformeConfig.query.filter_by(nom=nom).first():
        #     return jsonify({"error": f"La plateforme {nom} existe déjà"}), 400

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
    current_user_id = get_jwt_identity() 
    current_user = Utilisateur.query.get(current_user_id)
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401 
    try:
        plateformes = PlateformeConfig.get_active_platforms()
        return jsonify([p.to_dict() for p in plateformes]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_plateforme_by_id(plateforme_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    if not current_user_id:
        return jsonify({"error":"Authentification requise"}), 401
    plateforme = PlateformeConfig.query.get(plateforme_id)
    if not plateforme:
        return jsonify({"error": "Plateforme introuvable"}), 404

    return jsonify(plateforme.to_dict()), 200


def update_plateforme(plateforme_id):
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


