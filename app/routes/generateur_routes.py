from flask import Blueprint
from app.controllers import generateur_controller

ollama_bp = Blueprint('ollama', __name__)

@ollama_bp.route('/', methods=['POST'])
def handle_ollama():
    return generateur_controller.ollama_test()
