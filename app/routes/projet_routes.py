from flask import Blueprint
from app.controllers import projet_controller
from app.extensions import db
from flask import request

projet_bp = Blueprint('projet_bp', __name__)

@projet_bp.route("/", methods=["GET"])
def get_all_projet():
    return projet_controller.get_all_projet()

