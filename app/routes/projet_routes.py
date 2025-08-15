# from app.controllers import projet_controller

from flask import Blueprint, request, jsonify
from app.models.projet import Projet, TypeStatusEnum
from app.controllers import projet_controller
from app.extensions import db
from datetime import datetime
import json

projet_bp = Blueprint('projet', __name__)

@projet_bp.route('', methods=['GET', 'POST', 'OPTIONS'])
def handle_projets():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    elif request.method == 'GET':
        return projet_controller.get_all_projet()
    elif request.method == 'POST':
        return projet_controller.create_projet()

@projet_bp.route('/<int:projet_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def handle_projet(projet_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    elif request.method == 'GET':
        return projet_controller.get_projet_by_id(projet_id)
    elif request.method == 'PUT':
        return projet_controller.update_projet(projet_id)
    elif request.method == 'DELETE':
        return projet_controller.delete_projet(projet_id)

