from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.controllers.whisper_controller import transcribe_audio
import os

api_bp = Blueprint('api', __name__)
UPLOAD_FOLDER = os.path.abspath('uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a'}

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.route("/transcribe", methods=["POST"])
def transcribe():
  if "file" not in request.files:
    return jsonify({'error': 'Aucun fichier envoyé'}), 400

  file = request.files["file"]
  if file.filename == '' or not allowed_file(file.filename):
    return jsonify({'error': 'Type de fichier non supporté'}), 400

  filename = secure_filename(file.filename)
  filepath = os.path.join(UPLOAD_FOLDER, filename)
  file.save(filepath)

  try:
    transcription = transcribe_audio(filepath)
  except Exception as e:
    os.remove(filepath)
    return jsonify({'error': 'Erreur lors de la transcription', 'details': str(e)}), 500

  os.remove(filepath)
  return jsonify({"transcription": transcription})