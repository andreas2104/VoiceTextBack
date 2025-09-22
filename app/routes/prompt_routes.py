from flask import Blueprint,jsonify
from app.controllers import prompt_controller
from flask_jwt_extended import jwt_required


prompt_bp = Blueprint('prompt_bp', __name__, url_prefix="")


@prompt_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_prompt():
    return prompt_controller.get_all_prompt() 

@prompt_bp.route('/', methods=['POST'], strict_slashes=False)
@jwt_required()
def create_prompt():
    return prompt_controller.create_prompt()

@prompt_bp.route("/<int:prompt_id>", methods=["GET"])
@jwt_required()
def get_prompt_by_id(prompt_id):
    return prompt_controller.get_prompt_by_id(prompt_id=prompt_id)

@prompt_bp.route('/<int:prompt_id>', methods=['PUT'])
@jwt_required()
def update_prompt(prompt_id):
    return prompt_controller.update_prompt(prompt_id=prompt_id)

@prompt_bp.route('/<int:prompt_id>', methods=['DELETE'])
@jwt_required()
def delete_prompt(prompt_id):
    return prompt_controller.delete_prompt(prompt_id=prompt_id)