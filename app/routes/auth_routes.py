from flask import Blueprint
from app.controllers import auth_controller
from flask_jwt_extended import jwt_required

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    return auth_controller.register()

@auth_bp.route("/login", methods=["POST"])
def login():
    return auth_controller.login()

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    return auth_controller.me()

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    return auth_controller.refresh()

@auth_bp.route("/logout", methods=["POST"])
def logout():
    return auth_controller.logout()
