from flask import request, jsonify
from app.models.user import User, TypeCompteEnum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


def get_all_Users():
    try:
        users = User.query.all()
        users_data = [{
            'id':user.id,
            'nom': user.nom,
            'prenom': user.prenom,
            'email': user.email,
            'type_compte': user.type_compte.value,
            'date_creation': user.date_creation.isoformat(),
            'actif': user.actif
        } for user in users]
        return jsonify(users_data), 200
    except Exception as e:  
        return jsonify({"error": str(e)}), 500
    

def get_User_by_id(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'id': user.id,
        'nom': user.nom,
        'prenom': user.prenom,
        'email': user.email,
        'type_compte': user.type_compte.value,
        'date_creation': user.date_creation.isoformat(),
        'actif': user.actif
    }), 200    


def create_User(data):
    data = request.json
    if not data or not all(key in data for key in ['nom', 'prenom', 'email', 'mot_de_passe']):
        return {"error": "Missing required fields"}, 400
    
    try:
        hashed_password =  generate_password_hash(data['mot_de_passe'])
        new_user = User(
            nom=data['nom'],
            prenom=data['prenom'],
            email=data['email'],
            mot_de_passe=hashed_password,
            type_compte=data.get('type_compte', TypeCompteEnum.user),
            actif=data.get('actif', True)
            
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "message": "User created successfully",
            "user_id": new_user.id,
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
def update_User(user_id, data):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if 'mot_de_passe' in data:
        data['mot_de_passe'] = generate_password_hash(data['mot_de_passe'])
    
    for key, value in data.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    try:
        db.session.commit()
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

def delete_User(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400