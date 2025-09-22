from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.controllers import projet_controller


projet_bp = Blueprint("projet_bp", __name__, url_prefix="/")


@projet_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_projet():
    return projet_controller.get_all_projet()


@projet_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_projet():
    return projet_controller.create_projet()


@projet_bp.route("/<int:projet_id>", methods=["GET"])
@jwt_required()
def get_projet_by_id(projet_id):
    return projet_controller.get_projet_by_id(projet_id=projet_id)


@projet_bp.route("/<int:projet_id>", methods=["PUT"])
@jwt_required()
def update_projet(projet_id):
    return projet_controller.update_projet(projet_id=projet_id)


@projet_bp.route("/<int:projet_id>", methods=["DELETE"])
@jwt_required()
def delete_projet(projet_id):
    return projet_controller.delete_projet(projet_id=projet_id)
