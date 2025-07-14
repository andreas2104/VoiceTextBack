from flask import Blueprint
from app.controllers import prompt_controller
from app.extensions import db
from flask import request

prompt_bp = Blueprint('prompt_bp', __name__)

@prompt_bp.route("/", methods=["GET"])
def get_all_prompt():
    return prompt_controller.get_all_prompt() 

@prompt_bp.route('/', methods=['POST'])
def create_prompt():
    return prompt_controller.create_prompt()

@prompt_bp.route("/<int:prompt_id>", methods=["GET"])
def get_prompt_by_id(prompt_id):
    return prompt_controller.get_prompt_by_id(prompt_id=prompt_id)

@prompt_bp.route('/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    return prompt_controller.update_prompt(prompt_id=prompt_id)

@prompt_bp.route('/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    return prompt_controller.delete_prompt(prompt_id=prompt_id)