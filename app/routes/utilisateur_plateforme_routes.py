from flask import Blueprint
from app.controllers import utilisateur_plateforme_controller
from flask_jwt_extended import jwt_required

utilisateur_plateforme_bp = Blueprint('utilisateur_plateforme_bp', __name__, url_prefix='/api/user-plateformes')

@utilisateur_plateforme_bp.route("/", methods=['GET'], strict_slashes=False)
@jwt_required()
def get_user_plateformes():
    """Liste toutes les plateformes connectées de l'utilisateur"""
    return utilisateur_plateforme_controller.get_user_plateformes()

@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>", methods=['GET'], strict_slashes=False)
@jwt_required()
def get_user_plateforme_by_id(user_plateforme_id):
    """Récupère une connexion plateforme spécifique"""
    return utilisateur_plateforme_controller.get_user_plateforme_by_id(user_plateforme_id)

@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>", methods=["DELETE"], strict_slashes=False)
@jwt_required()
def disconnect_user_plateforme(user_plateforme_id):
    """Déconnecte un utilisateur d'une plateforme"""
    return utilisateur_plateforme_controller.disconnect_user_plateforme(user_plateforme_id)


@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>/meta", methods=["PUT"], strict_slashes=False)
@jwt_required()
def update_user_plateforme_meta(user_plateforme_id):
    """Met à jour les métadonnées d'une connexion plateforme"""
    return utilisateur_plateforme_controller.update_user_plateforme_meta(user_plateforme_id)


@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>/token", methods=["PUT"], strict_slashes=False)
@jwt_required()
def refresh_token(user_plateforme_id):
    """Rafraîchit le token d'accès d'une connexion plateforme"""
    return utilisateur_plateforme_controller.refresh_token(user_plateforme_id)


@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>/check-token", methods=["GET"], strict_slashes=False)
@jwt_required()
def check_token_validity(user_plateforme_id):
    """Vérifie la validité du token d'une connexion plateforme"""
    return utilisateur_plateforme_controller.check_token_validity(user_plateforme_id)


@utilisateur_plateforme_bp.route("/oauth/<string:plateforme_nom>/initiate", methods=["GET"], strict_slashes=False)
@jwt_required()
def initiate_oauth(plateforme_nom):
    """Initialise le flux OAuth pour une plateforme"""
    return utilisateur_plateforme_controller.initiate_oauth(plateforme_nom)


@utilisateur_plateforme_bp.route("/oauth/<string:plateforme_nom>/callback", methods=["GET"], strict_slashes=False)
def oauth_callback(plateforme_nom):
    """Gère le callback OAuth (pas de jwt_required car appelé par la plateforme externe)"""
    return utilisateur_plateforme_controller.oauth_callback(plateforme_nom)


@utilisateur_plateforme_bp.route("/admin/cleanup-states", methods=["POST"], strict_slashes=False)
@jwt_required()
def cleanup_expired_states():
    """Nettoie les states OAuth expirés (réservé admin)"""
    return utilisateur_plateforme_controller.cleanup_expired_states()