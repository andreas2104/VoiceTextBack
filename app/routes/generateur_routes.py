from flask import Blueprint
from app.controllers import generateur_controller
from flask import request

generateur_bp = Blueprint('generateur_bp', __name__)

@generateur_bp.route("/", methods=["POST"])
def create_contenu():
  return generateur_controller.generer_contenu()

