from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers import utilisateur_plateforme_controller

# CORRECTION 1: Préfixe URL cohérent avec le service frontend
plateforme_bp = Blueprint("plateforme_bp", __name__, url_prefix="/plateformes")


@plateforme_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_user_plateformes_route():
    """
    Récupère la liste des plateformes connectées pour l'utilisateur courant.
    Route: GET /plateformes/
    """
    return utilisateur_plateforme_controller.get_user_plateformes()


@plateforme_bp.route("/<int:plateforme_id>", methods=["DELETE"])
@jwt_required()
def disconnect_plateforme_route(plateforme_id):
    """
    Déconnecte une plateforme spécifique de l'utilisateur.
    Route: DELETE /plateformes/{plateforme_id}
    CORRECTION 2: Nom de fonction cohérent avec le controller
    """
    return utilisateur_plateforme_controller.disconnect_plateforme(plateforme_id=plateforme_id)


@plateforme_bp.route("/oauth/<string:plateforme_nom>/login", methods=["GET"])
@jwt_required() 
def initier_oauth_route(plateforme_nom):
    """
    Démarre le flux OAuth en redirigeant l'utilisateur vers la plateforme externe.
    Route: GET /plateformes/oauth/{plateforme_nom}/login
    CORRECTION 3: Nom de fonction cohérent avec le controller
    """
    return utilisateur_plateforme_controller.initier_connexion_oauth(plateforme_nom=plateforme_nom)


@plateforme_bp.route("/oauth/<string:plateforme_nom>/callback", methods=["GET"])
def callback_oauth_route(plateforme_nom):
    """
    Gère la réponse de la plateforme OAuth après authentification.
    Route: GET /plateformes/oauth/{plateforme_nom}/callback
    NOTE: jwt_required n'est pas utilisé ici car la connexion utilisateur est gérée par le 'state' token.
    CORRECTION 4: Nom de fonction cohérent avec le controller et les url_for()
    """
    return utilisateur_plateforme_controller.callback_oauth(plateforme_nom=plateforme_nom)


# AJOUT: Route pour obtenir le statut de toutes les plateformes disponibles
@plateforme_bp.route("/status", methods=["GET"])
@jwt_required()
def get_plateformes_status_route():
    """
    Récupère le statut de connexion pour toutes les plateformes disponibles.
    Route: GET /plateformes/status
    """
    return utilisateur_plateforme_controller.get_plateforme_status()


# AJOUT: Route pour rafraîchir un token expiré
@plateforme_bp.route("/<int:plateforme_id>/refresh", methods=["POST"])
@jwt_required()
def refresh_token_route(plateforme_id):
    """
    Rafraîchit le token d'accès pour une plateforme spécifique.
    Route: POST /plateformes/{plateforme_id}/refresh
    """
    return utilisateur_plateforme_controller.refresh_plateforme_token(plateforme_id=plateforme_id)