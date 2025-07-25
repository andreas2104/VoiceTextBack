from flask import Blueprint, request
from app.controllers import contenu_controller

contenu_bp = Blueprint("contenu_bp", __name__)

@contenu_bp.route("/", methods=["POST"])
def create_contenu():
  return contenu_controller.generer_contenu()