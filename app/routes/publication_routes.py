from flask import Blueprint, jsonify
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import jwt_required
from app.controllers import publication_controller

publication_bp = Blueprint("publication_bp", __name__, url_prefix="/publications")

@publication_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_publications():
    return publication_controller.get_all_publications()

@publication_bp.route("/<int:publication_id>", methods=["GET"])
@jwt_required()
def get_publication_by_id(publication_id):
    return publication_controller.get_publication_by_id(publication_id)

@publication_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_publication():
    return publication_controller.create_publication()

@publication_bp.route("/<int:publication_id>", methods=["PUT"])
@jwt_required()
def update_publication(publication_id):
    return publication_controller.update_publication(publication_id)

@publication_bp.route("/<int:publication_id>", methods=["DELETE"])
@jwt_required()
def delete_publication(publication_id):
    return publication_controller.delete_publication(publication_id)


@publication_bp.route('/stats', methods=["GET"])
@jwt_required()
def get_publication_stats():
    return publication_controller.get_publication_stats()


@publication_bp.route("/<int:publication_id>/annuler", methods=["POST"])
@jwt_required()
def annuler_publication(publication_id):
    return publication_controller.annuler_publication_programmee(publication_id)

