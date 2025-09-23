from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers import contenu_controller

contenu_bp = Blueprint("contenu_bp", __name__, url_prefix="/contenu")


@contenu_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_contenus():
    return contenu_controller.get_all_contenus()


@contenu_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_contenu():
    return contenu_controller.generer_contenu()


@contenu_bp.route("/<int:contenu_id>", methods=["GET"])
@jwt_required()
def get_contenu_by_id(contenu_id):
    return contenu_controller.get_contenu_by_id(contenu_id)


@contenu_bp.route("/<int:contenu_id>", methods=["PUT"])
@jwt_required()
def update_contenu(contenu_id):
    return contenu_controller.update_contenu(contenu_id)


@contenu_bp.route("/<int:contenu_id>", methods=["DELETE"])
@jwt_required()
def delete_contenu(contenu_id):
    return contenu_controller.delete_contenu(contenu_id)
