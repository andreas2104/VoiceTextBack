from flask import Blueprint
from app.controllers import utilisateur_controller
from app.extensions import db
from flask import request


utilisateur_bp = Blueprint('utilisateur_bp', __name__)

@utilisateur_bp.route("/test")
def test_route():
    return "Connection works!", 200

@utilisateur_bp.route("/", methods=["GET"])
def get_all_utilisateur():
    return utilisateur_controller.get_all_utilisateur()

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["GET"])
def get_utilisateur_by_id(utilisateur_id):
    return utilisateur_controller.get_utilisateur_by_id(utilisateur_id)

@utilisateur_bp.route("/", methods=["POST"])
def create_utilisateur():
    return utilisateur_controller.create_utilisateur(request.json)

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["PUT"])
def update_utilisateur(utilisateur_id):
    return utilisateur_controller.update_utilisateur(utilisateur_id, request.json)

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["DELETE"])
def delete_utilisateur(utilisateur_id):
    return utilisateur_controller.delete_utilisateur(utilisateur_id)
