from flask import Blueprint
from app.controllers import user_controller

user_bp = Blueprint('user_bp', __name__)

user_bp.route("/", methods=["GET"])(user_controller.get_all_Users)
user_bp.route("/<int:user_id>", methods=["GET"])(user_controller.get_User_by_id)
user_bp.route("/", methods=["POST"])(user_controller.create_User)
user_bp.route("/<int:user_id>", methods=["PUT"])(user_controller.update_User)
user_bp.route("/<int:user_id>", methods=["DELETE"])(user_controller.delete_User)