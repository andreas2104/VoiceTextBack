from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers import historique_controller

historique_bp = Blueprint("historique_bp", __name__, url_prefix="/historiques")

@historique_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_historiques():
    return historique_controller.get_all_historiques()

@historique_bp.route("/contenu/<int:contenu_id>", methods=["GET"])
@jwt_required()
def get_historique_by_contenu(contenu_id):
    return historique_controller.get_historique_by_contenu(contenu_id)

