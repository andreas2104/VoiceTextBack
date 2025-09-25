
from flask import request, jsonify
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required, get_jwt, unset_jwt_cookies
import os

ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(",")
def register():

    data = request.json
    if not data or not all(key in data for key in ['nom', 'prenom', 'email', 'mot_de_passe']):
        return jsonify({"error": "Missing required fields"}), 400   

    if Utilisateur.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 409

    try:
        hashed_password = generate_password_hash(data['mot_de_passe'])
        
        new_utilisateur = Utilisateur(
            nom=data['nom'],
            prenom=data['prenom'],
            email=data['email'],
            mot_de_passe=hashed_password,
            type_compte=TypeCompteEnum.user,
            actif=True
        )
        db.session.add(new_utilisateur)
        db.session.commit()
        return jsonify({
            "message": "Utilisateur created successfully",
            "utilisateur_id": new_utilisateur.id,
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def login():
 
    data = request.json
    if not data or not all(key in data for key in ['email', 'mot_de_passe']):
        return jsonify({"error": "Missing required fields"}), 400

    utilisateur = Utilisateur.query.filter_by(email=data['email']).first()
    
    if not utilisateur or not check_password_hash(utilisateur.mot_de_passe, data['mot_de_passe']):
        return jsonify({"error": "Invalid email or password"}), 401
    
    if utilisateur.email.lower() in [e.lower() for e in ADMIN_EMAILS]:
        if utilisateur.type_compte != TypeCompteEnum.admin:
            utilisateur.type_compte = TypeCompteEnum.admin
            db.session.commit()
  
    access_token = create_access_token(identity=utilisateur.id)
    refresh_token = create_refresh_token(identity=utilisateur.id)
    return jsonify(access_token=access_token,refresh_token=refresh_token), 200


