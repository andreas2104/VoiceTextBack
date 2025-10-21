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
        
        access_token = create_access_token(
            identity=new_utilisateur.id,
            additional_claims={
                'email': new_utilisateur.email,
                'type_compte': new_utilisateur.type_compte.value
            }
        )
        refresh_token = create_refresh_token(identity=new_utilisateur.id)

        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "utilisateur": {
                "id": new_utilisateur.id,
                "email": new_utilisateur.email,
                "nom": new_utilisateur.nom,
                "prenom": new_utilisateur.prenom,
                "type_compte": new_utilisateur.type_compte.value
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def login():
    data = request.json
    
    
    print('📥 Données reçues:', data)
    
    if not data or not all(key in data for key in ['email', 'mot_de_passe']):
        return jsonify({"error": "Missing required fields"}), 422  

    utilisateur = Utilisateur.query.filter_by(email=data['email']).first()
    
    if not utilisateur:
        return jsonify({"error": "Invalid email or password"}), 401
    
    if not utilisateur.mot_de_passe:
        return jsonify({"error": "Please login with Google or X"}), 401
    
    if not check_password_hash(utilisateur.mot_de_passe, data['mot_de_passe']):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Promouvoir en admin si nécessaire
    if utilisateur.email.lower() in [e.lower() for e in ADMIN_EMAILS if e]:
        if utilisateur.type_compte != TypeCompteEnum.admin:
            utilisateur.type_compte = TypeCompteEnum.admin
            db.session.commit()

    access_token = create_access_token(
        identity=utilisateur.id,
        additional_claims={
            'email': utilisateur.email,
            'type_compte': utilisateur.type_compte.value
        }
    )
    refresh_token = create_refresh_token(identity=utilisateur.id)
    
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "utilisateur": {
            "id": utilisateur.id,
            "email": utilisateur.email,
            "nom": utilisateur.nom,
            "prenom": utilisateur.prenom,
            "type_compte": utilisateur.type_compte.value,
            "photo": utilisateur.photo
        }
    }), 200