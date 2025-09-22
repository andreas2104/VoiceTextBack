from flask import Blueprint
from app.controllers import modelIA_controller
from app.extensions import db
from flask import request

modelIA_bp = Blueprint('modelIA_bp', __name__, url_prefix="/")



@modelIA_bp.route("/", methods=["GET"],strict_slashes=False)
def get_all_modelIA():
    return modelIA_controller.get_all_modelIA()

@modelIA_bp.route("/", methods=["POST"], strict_slashes=False)
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

