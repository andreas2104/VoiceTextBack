from flask import Blueprint
from app.controllers import modelIA_controller
from app.extensions import db
from flask import request

modelIA_bp = Blueprint('modelIA_bp', __name__)



@modelIA_bp.route("/", methods=["GET"])
def test_route():
    return "Connection works!", 200

@modelIA_bp.route("/", methods=["POST"])
def create_modelIA():
    return modelIA_controller.create_modelIA()

@modelIA_bp.route("/<int:modelIA_id>", methods=["GET"])
def get_modelIA_by_id(modelIA_id):
    return modelIA_controller.get_modelIA_by_id(modelIA_id=modelIA_id)

@modelIA_bp.route("/<int:modelIA_id>", methods=["PUT"])
def update_modelIA(modelIA_id):
    return modelIA_controller.update_modelIA(modelIA_id=modelIA_id)   

@modelIA_bp.route("/<int:modelIA_id>", methods=["DELETE"])
def delete_modelIA(modelIA_id):
    return modelIA_controller.delete_modelIA(modelIA_id=modelIA_id) 

