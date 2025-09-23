from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers import plateforme_controller

plateforme_bp = Blueprint("plateforme_bp", __name__, url_prefix="/plateformes")

# Routes de base
@plateforme_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_plateformes():
    """Récupère les plateformes de l'utilisateur"""
    return plateforme_controller.get_all_plateformes()

@plateforme_bp.route("/<int:plateforme_id>", methods=["GET"])
@jwt_required()
def get_plateforme_by_id(plateforme_id):
    """Récupère une plateforme par son ID"""
    return plateforme_controller.get_plateforme_by_id(plateforme_id)

# Routes spécifiques aux réseaux sociaux
@plateforme_bp.route("/connecter", methods=["POST"])
@jwt_required()
def connecter_plateforme():
    """Connecte Facebook ou LinkedIn via OAuth"""
    return plateforme_controller.connecter_plateforme()

@plateforme_bp.route("/publier", methods=["POST"])
@jwt_required()
def publier_contenu():
    """Publie un contenu sur une plateforme"""
    return plateforme_controller.publier_contenu()

@plateforme_bp.route("/<int:plateforme_id>/statistiques", methods=["GET"])
@jwt_required()
def get_statistiques_plateforme(plateforme_id):
    """Récupère les statistiques d'une plateforme"""
    return plateforme_controller.get_statistiques_plateforme(plateforme_id)

@plateforme_bp.route("/<int:plateforme_id>/verifier-token", methods=["POST"])
@jwt_required()
def verifier_token_plateforme(plateforme_id):
    """Vérifie la validité du token d'une plateforme"""
    return plateforme_controller.verifier_token_plateforme(plateforme_id)

@plateforme_bp.route("/<int:plateforme_id>/deconnecter", methods=["POST"])
@jwt_required()
def deconnecter_plateforme(plateforme_id):
    """Déconnecte une plateforme"""
    return plateforme_controller.deconnecter_plateforme(plateforme_id)

# Routes de configuration
@plateforme_bp.route("/<int:plateforme_id>/parametres", methods=["PUT"])
@jwt_required()
def update_parametres_plateforme(plateforme_id):
    """Met à jour les paramètres d'une plateforme"""
    return plateforme_controller.update_parametres_plateforme(plateforme_id)

