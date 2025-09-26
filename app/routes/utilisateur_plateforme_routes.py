from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers import utilisateur_plateforme_controller

plateforme_bp = Blueprint("plateforme_bp", __name__, url_prefix="/")


@plateforme_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_user_plateformes_route():
    """
    Récupère la liste des plateformes connectées pour l'utilisateur courant.
    """
    return utilisateur_plateforme_controller.get_user_plateformes()


@plateforme_bp.route("/<int:plateforme_id>", methods=["DELETE"])
@jwt_required()
def disconnect_platforme_route(plateforme_id):
    """
    Déconnecte une plateforme spécifique de l'utilisateur.
    """
    return utilisateur_plateforme_controller.disconnect_platforme(plateforme_id=plateforme_id)


@plateforme_bp.route("/oauth/<string:plateforme_nom>/login", methods=["GET"])
@jwt_required() 
def start_oauth_route(plateforme_nom):
    """
    Démarre le flux OAuth en redirigeant l'utilisateur vers la plateforme externe.
    """
    return utilisateur_plateforme_controller.start_oauth(plateforme_nom=plateforme_nom)


@plateforme_bp.route("/oauth/<string:plateforme_nom>/callback", methods=["GET"])
def handle_oauth_callback_route(plateforme_nom):
    """
    Gère la réponse de la plateforme OAuth après authentification.
    NOTE: jwt_required n'est pas utilisé ici car la connexion utilisateur est gérée par le 'state' token.
    """
    return utilisateur_plateforme_controller.handle_oauth_callback(plateforme_nom=plateforme_nom)
