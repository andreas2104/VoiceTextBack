from flask import Blueprint
from app.controllers import generateur_controller
from flask import request

contenu_bp = Blueprint('contenu_bp', __name__)

@contenu_bp.route("/", methods=["POST"])
def create_contenu():
  return generateur_controller.generer_contenu()

