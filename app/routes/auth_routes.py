from app.utils.identity import get_identity
from flask import Blueprint, jsonify
from app.controllers import auth_controller
from flask_jwt_extended import jwt_required

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    return auth_controller.register()

@auth_bp.route("/login", methods=["POST"])
def login():
    return auth_controller.login()

@auth_bp.route("/protected", methods=['GET'])
@jwt_required()
def protected_route():
    current_user_id = get_identity()
    return jsonify(message=f'Hello, user {current_user_id}! You have access to the protected resource.'), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me_route():
    return auth_controller.get_me()

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    return auth_controller.refresh()

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return auth_controller.logout()
