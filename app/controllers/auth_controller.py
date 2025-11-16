from flask import request, jsonify, make_response
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,  
    jwt_required, 
    get_jwt, 
    unset_jwt_cookies,
    set_access_cookies,
    set_refresh_cookies
)
import os
from app.utils.identity import  get_identity

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
        refresh_token = create_refresh_token(identity=str(new_utilisateur.id))

        response = make_response(jsonify({
            "message": "Inscription réussie",
            "utilisateur": {
                "id": new_utilisateur.id,
                "email": new_utilisateur.email,
                "nom": new_utilisateur.nom,
                "prenom": new_utilisateur.prenom,
                "type_compte": new_utilisateur.type_compte.value
            }
        }), 201)
        
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        
        print(f" Registration successful for {new_utilisateur.email}")
        print(f" Cookies set: access_token, refresh_token")
        
        return response
        
    except Exception as e:
        db.session.rollback()
        print(f" Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500


def login():
    data = request.json
    if not data or not all(key in data for key in ['email', 'mot_de_passe']):
        return jsonify({"error": "Missing required fields"}), 422  

    utilisateur = Utilisateur.query.filter_by(email=data['email']).first()
    
    if not utilisateur:
        return jsonify({"error": "Invalid email or password"}), 401
    
    if not utilisateur.mot_de_passe:
        return jsonify({"error": "Please login with Google or X"}), 401
    
    if not check_password_hash(utilisateur.mot_de_passe, data['mot_de_passe']):
        return jsonify({"error": "Invalid email or password"}), 401
    
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

    response = make_response(jsonify({
        "message": "Connexion réussie",
        "utilisateur": {
            "id": utilisateur.id,
            "email": utilisateur.email,
            "nom": utilisateur.nom,
            "prenom": utilisateur.prenom,
            "type_compte": utilisateur.type_compte.value,
            "photo": utilisateur.photo
        }
    }), 200)
    
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    
    print(f"Login successful for {utilisateur.email}")
    print(f"Cookies set: access_token, refresh_token")
    
    return response


@jwt_required()
def get_me():
    try:
        current_user_id = get_jwt_identity()
        utilisateur = Utilisateur.query.get(current_user_id)
        
        if not utilisateur:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
            
        return jsonify({
            "utilisateur": {
                "id": utilisateur.id,
                "email": utilisateur.email,
                "nom": utilisateur.nom,
                "prenom": utilisateur.prenom,
                "type_compte": utilisateur.type_compte.value,
                "photo": utilisateur.photo
            }
        }), 200
    except Exception as e:
        print(f" Get me error: {str(e)}")
        return jsonify({"error": str(e)}), 401


@jwt_required(refresh=True)
def refresh():
    try:
        print("🔍 Refresh endpoint called")
        current_user_id = get_jwt_identity()
        print(f"🔍 User ID from refresh token: {current_user_id}")
        
        utilisateur = Utilisateur.query.get(current_user_id)
        if not utilisateur:
            print(f" User {current_user_id} not found in database")
            return jsonify({"error": "User not found"}), 404
        
        new_access_token = create_access_token(
            identity=current_user_id,
            additional_claims={
                'email': utilisateur.email,
                'type_compte': utilisateur.type_compte.value
            }
        )
        
        response = make_response(jsonify({"message": "Token rafraîchi"}), 200)
        set_access_cookies(response, new_access_token)
        
        print(f" Token refreshed for user {current_user_id}")
        
        return response
        
    except Exception as e:
        print(f" Refresh error: {str(e)}")
        import traceback
        traceback.print_exc()  
        return jsonify({"error": str(e)}), 401


def logout():
    try:
    
        response = make_response(jsonify({"message": "Déconnexion réussie"}), 200)
        unset_jwt_cookies(response)
        
        print("Logout successful, cookies cleared")
        
        return response
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({"error": str(e)}), 500