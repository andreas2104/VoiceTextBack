from flask import Blueprint
from app.controllers import oauth_controller


oauth_bp = Blueprint('oauth_bp', __name__, url_prefix='/api/oauth')


@oauth_bp.route('/login/google', methods=['GET'])
def login_google_route():
    """Route pour initier la connexion Google OAuth"""
    return oauth_controller.login_google()

@oauth_bp.route('/google/callback', methods=['GET'])
def google_callback_route():
    """Route de callback Google OAuth"""
    return oauth_controller.google_callback()


@oauth_bp.route('/login/x', methods=['GET'])
def login_x_route():
    """Route pour initier la connexion X OAuth"""
    return oauth_controller.login_x()

@oauth_bp.route('/x/callback', methods=['GET'])
def x_callback_route():
    """Route de callback X OAuth"""
    return oauth_controller.x_callback()


@oauth_bp.route('/logout', methods=['POST'])
def oauth_logout_route():
    """Route de déconnexion OAuth"""
    return oauth_controller.oauth_logout()

@oauth_bp.route('/x/debug', methods=['GET'])
def x_debug_route():
    """Route de debug X OAuth"""
    return oauth_controller.x_debug()