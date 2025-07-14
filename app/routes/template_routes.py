from flask import Blueprint
from app.controllers import template_controller
from app.extensions import db
from flask import request

template_bp = Blueprint('template_bp', __name__)

@template_bp.route("/", methods=['GET'])
def get_all_template():
  return template_controller.get_all_template()

@template_bp.route("/",methods=['POST'])
def create_template():
  return template_controller.create_template()

@template_bp.route("/<int:projet_id>", methods=['GET'])
def get_template_by_id(template_id):
  return template_controller.get_template_by_id(template_id)

@template_bp.route("/<int:projet_id>", methods=["PUT"])
def update_template(template_id):
  return template_controller.update_template(template_id=template_id)

@template_bp.route("/<int:template_id>", methods=['DELETE'])
def delete_template(template_id):
  return template_controller.delete_template(template_id=template_id)
