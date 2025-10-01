from flask import Blueprint
from app.controllers import modelIA_controller
from app.extensions import db
from flask import request
from flask_jwt_extended import jwt_required

modelIA_bp = Blueprint('modelIA_bp', __name__, url_prefix="/")

@modelIA_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_modelIA_route():
    return modelIA_controller.get_all_modelIA()

@modelIA_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_modelIA_route():
    return modelIA_controller.create_modelIA()

@modelIA_bp.route("/<int:modelIA_id>", methods=["GET"])
@jwt_required()
def get_modelIA_by_id_route(modelIA_id):
    return modelIA_controller.get_modelIA_by_id(modelIA_id=modelIA_id)

@modelIA_bp.route("/<int:modelIA_id>", methods=["PUT"])
@jwt_required()
def update_modelIA_route(modelIA_id):
    return modelIA_controller.update_modelIA(modelIA_id=modelIA_id)   

@modelIA_bp.route("/<int:modelIA_id>", methods=["DELETE"])
@jwt_required()
def delete_modelIA_route(modelIA_id):
    return modelIA_controller.delete_modelIA(modelIA_id=modelIA_id)

@modelIA_bp.route("/<int:modelIA_id>/toggle", methods=["PATCH"])
@jwt_required()
def toggle_model_activation_route(modelIA_id):
    return modelIA_controller.toggle_model_activation(modelIA_id=modelIA_id)

@modelIA_bp.route("/active", methods=["GET"])
@jwt_required()
def get_active_models_route():
    return modelIA_controller.get_active_models()

@modelIA_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_models_stats_route():
    return modelIA_controller.get_models_stats()