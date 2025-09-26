from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.plateforme_controller import (
    create_plateforme,
    get_plateformes,
    get_plateforme_by_id,
    update_plateforme,
    delete_plateforme,
    get_connexions_utilisateur,
    deconnexion_plateforme,
    initier_connexion_oauth,
    callback_oauth,
)

plateforme_config_bp = Blueprint("plateforme_config_bp", __name__, url_prefix="/")

# ---------- CRUD plateformes (admin) ----------
@plateforme_config_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def route_create_plateforme():
    return create_plateforme()

@plateforme_config_bp.route("", methods=["GET"], strict_slashes=False)
def route_get_plateformes():
    return get_plateformes()

@plateforme_config_bp.route("/<int:plateforme_id>", methods=["GET"])
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

# ---------- Connexions utilisateur ↔ plateforme ----------
@plateforme_config_bp.route("/connexions", methods=["GET"])
@jwt_required()
def route_get_connexions_utilisateur():
    return get_connexions_utilisateur()

@plateforme_config_bp.route("/connexions/<string:plateforme_nom>", methods=["DELETE"])
@jwt_required()
def route_deconnexion_plateforme(plateforme_nom):
    return deconnexion_plateforme(plateforme_nom)

# ---------- OAuth ----------
@plateforme_config_bp.route("/<string:plateforme_nom>/auth", methods=["POST"])
@jwt_required()
def route_initier_connexion(plateforme_nom):
    return initier_connexion_oauth(plateforme_nom)

@plateforme_config_bp.route("/<string:plateforme_nom>/callback", methods=["GET"])
def route_callback_oauth(plateforme_nom):
    return callback_oauth(plateforme_nom)
