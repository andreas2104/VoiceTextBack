from flask import Blueprint, request,jsonify,current_app
from app.controllers import utilisateur_controller
from app.extensions import db
# from werkzeug.security import check_password_hash
# from models import Utilisateur, TypeCompteEnum
# import datetime
# import jwt 
from flask import request


utilisateur_bp = Blueprint('utilisateur_bp', __name__)

# @utilisateur_bp.route('/login', methods=['POST'])
# def login():
#     """
#     Vérifie les informations de connexion et génère un JWT.
#     """
#     auth = request.json
#     if not auth or not auth.get('email') or not auth.get('password'):
#         return jsonify({"error": "Missing email or password"}), 400

#     email = auth.get('email')
#     mot_de_passe = auth.get('password')

#     utilisateur = Utilisateur.query.filter_by(email=email).first()

#     if not utilisateur or not check_password_hash(utilisateur.mot_de_passe, mot_de_passe):
#         return jsonify({"error": "Invalid email or password"}), 401

#     token_payload = {
#         'id': utilisateur.id,
#         'email': utilisateur.email,
#         'type_compte': utilisateur.type_compte.name,
#         'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
#     }

#     token = jwt.encode(
#         token_payload, 
#         current_app.config['SECRET_KEY'], 
#         algorithm='HS256'
#     )
#     return jsonify({"token": token}), 200

@utilisateur_bp.route("/", methods=["GET"])
def get_all_utilisateur():
    return utilisateur_controller.get_all_utilisateur()

@utilisateur_bp.route("/", methods=["POST"])
def create_utilisateur():
    return utilisateur_controller.create_utilisateur(request.json)

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["GET"])
def get_utilisateur_by_id(utilisateur_id):
    return utilisateur_controller.get_utilisateur_by_id(utilisateur_id)


@utilisateur_bp.route("/<int:utilisateur_id>", methods=["PUT"])
def update_utilisateur(utilisateur_id):
    return utilisateur_controller.update_utilisateur(utilisateur_id, request.json)

@utilisateur_bp.route("/<int:utilisateur_id>", methods=["DELETE"])
def delete_utilisateur(utilisateur_id):
    return utilisateur_controller.delete_utilisateur(utilisateur_id)
