from flask import  Blueprint, request, jsonify
from app.extensions import db
from app.models.utilisateur import Token
from datetime import datetime, timedelta
from flask_jwt_extended import get_jwt_identity

token_bp = Blueprint('token_bp', __name__)

@token_bp.route('/token',methods=['GET'])
def method_name():
    pass
def get_all_token():
  tokens = Token.query.all()
  print (f'fhello token stocker',{tokens})
  return jsonify([t.to_dict() for t in tokens]), 200