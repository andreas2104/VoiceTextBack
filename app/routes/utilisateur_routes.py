from flask import Blueprint
from app.controllers import utilisateur_controller
from flask_jwt_extended import jwt_required, get_jwt_identity


utilisateur_bp = Blueprint('utilisateur_bp', __name__)


@utilisateur_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_utilisateur():
    return utilisateur_controller.get_all_utilisateurs()

@utilisateur_bp.route("/", methods=["POST"])
def create_utilisateur():
    return utilisateur_controller.create_utilisateur()  

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["GET"])
@jwt_required()
def get_utilisateur_by_id(utilisateur_id):
    return utilisateur_controller.get_utilisateur_by_id(utilisateur_id)

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["PUT"])
@jwt_required()
def update_utilisateur(utilisateur_id):
    return utilisateur_controller.update_utilisateur(utilisateur_id)

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["DELETE"])
@jwt_required()
def delete_utilisateur(utilisateur_id):
    return utilisateur_controller.delete_utilisateur(utilisateur_id)

from app.utils.roles import roles_required
@utilisateur_bp.route("/me", methods=["GET"])
@jwt_required()
def current_utilisateur():
    return utilisateur_controller.current_utilisateur()

@utilisateur_bp.route("/admin-only", methods=["GET"])
@roles_required("admin")
def admin_only():
    return {"ok": True, "message": "Accès réservé aux admins"}, 200
