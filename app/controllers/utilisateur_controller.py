from flask import request, jsonify
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


def get_all_utilisateur():
    try:
        utilisateurs = Utilisateur.query.all()
        utilisateurs_data = [{
            'id':utilisateur.id,
            'nom': utilisateur.nom,
            'prenom': utilisateur.prenom,
            'email': utilisateur.email,
            'type_compte': utilisateur.type_compte.value,
            'date_creation': utilisateur.date_creation.isoformat(),
            'actif': utilisateur.actif
        } for utilisateur in utilisateurs]
        return jsonify(utilisateurs_data), 200
    except Exception as e:  
        return jsonify({"error": str(e)}), 500
    

def get_utilisateur_by_id(utilisateur_id):
    utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
    if not utilisateur:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'id': utilisateur.id,
        'nom': utilisateur.nom,
        'prenom': utilisateur.prenom,
        'email': utilisateur.email,
        'type_compte': utilisateur.type_compte.value,
        'date_creation': utilisateur.date_creation.isoformat(),
        'actif': utilisateur.actif
    }), 200    


def create_utilisateur(data):
    data = request.json
    if not data or not all(key in data for key in ['nom', 'prenom', 'email', 'mot_de_passe']):
        return {"error": "Missing required fields"}, 400
    
    try:
        hashed_password =  generate_password_hash(data['mot_de_passe'])
        new_utilisateur = Utilisateur(
            nom=data['nom'],
            prenom=data['prenom'],
            email=data['email'],
            mot_de_passe=hashed_password,
            type_compte=data.get('type_compte', TypeCompteEnum.user),
            actif=data.get('actif', True)
            
        )
        db.session.add(new_utilisateur)
        db.session.commit()
        return jsonify({
            "message": "Utilisateur created successfully",
            "utilisateur_id": new_utilisateur.id,
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
def update_utilisateur(utilisateur_id, data):
    utilisateur = Utilisateur.query.get(utilisateur_id)
    if not utilisateur:
        return jsonify({"error": "Utilisateur not found"}), 404
    
    if 'mot_de_passe' in data:
        data['mot_de_passe'] = generate_password_hash(data['mot_de_passe'])
    
    for key, value in data.items():
        if hasattr(utilisateur, key):
            setattr(utilisateur, key, value)
    
    try:
        db.session.commit()
        return jsonify({"message": "Utilisateur updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

def delete_utilisateur(utilisateur_id):
    utilisateur = Utilisateur.query.get(utilisateur_id)
    if not utilisateur:
        return jsonify({"error": "Utilisateur not found"}), 404
    
    try:
        db.session.delete(utilisateur)
        db.session.commit()
        return jsonify({"message": "Utilisateur deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400