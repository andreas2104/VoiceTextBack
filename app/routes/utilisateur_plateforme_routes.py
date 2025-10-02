from flask import Blueprint
from app.controllers import utilisateur_plateforme_controller
from flask_jwt_extended import jwt_required

utilisateur_plateforme_bp = Blueprint('utilisateur_plateforme_bp', __name__, url_prefix='/api/plateformes')

@utilisateur_plateforme_bp.route("/", methods=['GET'], strict_slashes=False)
@jwt_required()
def get_user_plateformes():
    return utilisateur_plateforme_controller.get_user_plateformes()

@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>", methods=['GET'], strict_slashes=False)
@jwt_required()
def get_user_plateforme_by_id(user_plateforme_id):

    return utilisateur_plateforme_controller.get_user_plateforme_by_id(user_plateforme_id)

@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>", methods=["DELETE"], strict_slashes=False)
@jwt_required()
def disconnect_user_plateforme(user_plateforme_id):
    return utilisateur_plateforme_controller.disconnect_user_plateforme(user_plateforme_id)


@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>/meta", methods=["PUT"], strict_slashes=False)
@jwt_required()
def update_user_plateforme_meta(user_plateforme_id):
    return utilisateur_plateforme_controller.update_user_plateforme_meta(user_plateforme_id)


@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>/token", methods=["PUT"], strict_slashes=False)
@jwt_required()
def refresh_token(user_plateforme_id):
    return utilisateur_plateforme_controller.refresh_token(user_plateforme_id)


@utilisateur_plateforme_bp.route("/<int:user_plateforme_id>/check-token", methods=["GET"], strict_slashes=False)
@jwt_required()
def check_token_validity(user_plateforme_id):
    return utilisateur_plateforme_controller.check_token_validity(user_plateforme_id)


@utilisateur_plateforme_bp.route("/oauth/<string:plateforme_nom>/initiate", methods=["GET"], strict_slashes=False)
@jwt_required()
def initiate_oauth(plateforme_nom):
    return utilisateur_plateforme_controller.initiate_oauth(plateforme_nom)


@utilisateur_plateforme_bp.route("/oauth/<string:plateforme_nom>/callback", methods=["GET"], strict_slashes=False)
def oauth_callback(plateforme_nom):
    return utilisateur_plateforme_controller.oauth_callback(plateforme_nom)


@utilisateur_plateforme_bp.route("/admin/cleanup-states", methods=["POST"], strict_slashes=False)
@jwt_required()
def cleanup_expired_states():
    return utilisateur_plateforme_controller.cleanup_expired_states()