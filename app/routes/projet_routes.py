from flask import Blueprint
from app.controllers import projet_controller
from app.extensions import db
from flask import request

projet_bp = Blueprint('projet_bp', __name__)

@projet_bp.route("/", methods=["GET"])
def get_all_projet():
    return projet_controller.get_all_projet()

@projet_bp.route("/", methods=["POST"])
def create_projet():
    return projet_controller.create_projet()

@projet_bp.route("/<int:projet_id>", methods=["GET"])
def get_projet_by_id(projet_id):
    return projet_controller.get_projet_by_id(projet_id=projet_id)


@projet_bp.route("/<int:projet_id>", methods=["PUT"])
def update_projet(projet_id):
    return projet_controller.update_projet(projet_id=projet_id)


@projet_bp.route("/<int:projet_id>", methods=["DELETE"])
def delete_projet(projet_id):
    return projet_controller.delete_projet(projet_id=projet_id) 