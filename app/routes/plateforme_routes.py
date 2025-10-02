from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.plateforme_controller import (
    create_plateforme,
    get_plateformes,
    get_plateforme_by_id,
    update_plateforme,
    delete_plateforme,

)

plateforme_config_bp = Blueprint("plateforme_config_bp", __name__, url_prefix="/")

@plateforme_config_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def route_create_plateforme():
    return create_plateforme()

@plateforme_config_bp.route("", methods=["GET"], strict_slashes=False)
@jwt_required()
def route_get_plateformes():
    return get_plateformes()

@plateforme_config_bp.route("/<int:plateforme_id>", methods=["GET"])
@jwt_required()
def route_get_plateforme_by_id(plateforme_id):
    return get_plateforme_by_id(plateforme_id)

@plateforme_config_bp.route("/<int:plateforme_id>", methods=["PUT"])
@jwt_required()
def route_update_plateforme(plateforme_id):
    return update_plateforme(plateforme_id)

@plateforme_config_bp.route("/<int:plateforme_id>", methods=["DELETE"])
@jwt_required()
def route_delete_plateforme(plateforme_id):
    return delete_plateforme(plateforme_id)
