from flask import Blueprint, request, jsonify
from app.controllers import contenu_controller

contenu_bp = Blueprint("contenu_bp", __name__)

# @contenu_bp.route("", methods=["POST"])
# def create_contenu():
#   return contenu_controller.generer_contenu()

# from flask import Blueprint, request, jsonify
# from app.controllers import contenu_controller
# contenu_bp = Blueprint("contenu_bp", __name__)

@contenu_bp.route("", methods=["GET", "POST", "OPTIONS"])
def handle_contenus(): 
  if request.method == "OPTIONS": return jsonify({}), 200
  elif request.method == "GET": return contenu_controller.get_all_contenus()
  elif request.method == "POST": return contenu_controller.generer_contenu() 

@contenu_bp.route("/<int:contenu_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
def handle_contenu(contenu_id):
  if request.method == "OPTIONS": return jsonify({}), 200 
  elif request.method == "GET": 
    return contenu_controller.get_contenu_by_id(contenu_id)
  elif request.method == "PUT": return contenu_controller.update_contenu(contenu_id)
  elif request.method == "DELETE": return contenu_controller.delete_contenu(contenu_id)