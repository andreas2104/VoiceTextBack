from flask import Blueprint
from app.controllers import template_controller
from flask_jwt_extended import jwt_required

# IMPORTANT: Ajouter strict_slashes=False
template_bp = Blueprint('template_bp', __name__, url_prefix="")

@template_bp.route("/", methods=['GET'], strict_slashes=False)
@jwt_required()
def get_all_template():
    return template_controller.get_all_template()

@template_bp.route("/", methods=['POST'], strict_slashes=False)
@jwt_required()
def create_template():
    return template_controller.create_template()

@template_bp.route("/<int:template_id>", methods=['GET'], strict_slashes=False)
@jwt_required()
def get_template_by_id(template_id):
    return template_controller.get_template_by_id(template_id)

@template_bp.route("/<int:template_id>", methods=["PUT"], strict_slashes=False)
@jwt_required()
def update_template(template_id):
    return template_controller.update_template(template_id)

@template_bp.route("/<int:template_id>", methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_template(template_id):
    return template_controller.delete_template(template_id)