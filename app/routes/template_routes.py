from flask import Blueprint
from app.controllers import template_controller
from flask_jwt_extended import jwt_required


template_bp = Blueprint('template_bp', __name__)

@template_bp.route("/", methods=['GET'])
@jwt_required()
def get_all_template():
  return template_controller.get_all_template()

@template_bp.route("/",methods=['POST'])
@jwt_required()
def create_template():
  return template_controller.create_template()

@template_bp.route("/<int:template_id>", methods=['GET'])
@jwt_required()
def get_template_by_id(template_id):
  return template_controller.get_template_by_id(template_id)

@template_bp.route("/<int:template_id>", methods=["PUT"])
@jwt_required()
def update_template(template_id):
  return template_controller.update_template(template_id)

@template_bp.route("/<int:template_id>", methods=['DELETE'])
@jwt_required()
def delete_template(template_id):
  return template_controller.delete_template(template_id)
