# app/routes.py

from flask import Blueprint, jsonify
from app.controllers import auth_controller
from flask_jwt_extended import jwt_required, get_jwt_identity

# Création d'un blueprint pour regrouper les routes d'authentification
auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    """Route pour l'enregistrement d'un nouvel utilisateur."""
    return auth_controller.register()

@auth_bp.route("/login", methods=["POST"])
def login():
    """Route pour la connexion et la génération des tokens."""
    return auth_controller.login()

@auth_bp.route("/protected", methods=['GET'])
@jwt_required()
def protected_route():
    """Exemple de route protégée par un token d'accès."""
    current_user_id = get_jwt_identity()
    return jsonify(message=f'Hello, user {current_user_id}! You have access to the protected resource.'), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me_route():
    """
    Route pour obtenir les informations de l'utilisateur actuel.
    Protégée par un token d'accès.
    """
    return auth_controller.get_me()

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Route pour rafraîchir le token d'accès en utilisant un token de rafraîchissement."""
    return auth_controller.refresh()

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Route pour déconnecter l'utilisateur en révoquant le token d'accès."""
    return auth_controller.logout()
