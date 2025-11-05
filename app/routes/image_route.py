from flask import Blueprint, send_from_directory
import os

uploads_bp = Blueprint('uploads_bp', __name__)

@uploads_bp.route('/uploads/images/<filename>')
def serve_image(filename):
    """Sert les fichiers images depuis le dossier uploads"""
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'uploads', 'images')
    return send_from_directory(UPLOAD_FOLDER, filename)