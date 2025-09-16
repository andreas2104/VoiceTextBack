from flask import request, jsonify
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import get_jwt_identity

def get_all_utilisateurs():
    """
    Récupère tous les utilisateurs. Accessible uniquement aux administrateurs.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = Utilisateur.query.get(current_user_id)

        if current_user.type_compte != TypeCompteEnum.admin:
            return jsonify({"error": "Unauthorized"}), 403
        
        utilisateurs = Utilisateur.query.all()
        utilisateurs_data = [{
            'id': utilisateur.id,
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
    """
    Récupère un utilisateur par son ID. Accessible à l'utilisateur lui-même ou aux administrateurs.
    """
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if current_user_id != utilisateur_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
    return jsonify({
        'id': utilisateur.id,
        'nom': utilisateur.nom,
        'prenom': utilisateur.prenom,
        'email': utilisateur.email,
        'type_compte': utilisateur.type_compte.value,
        'date_creation': utilisateur.date_creation.isoformat(),
        'actif': utilisateur.actif
    }), 200    

def update_utilisateur(utilisateur_id):
    """
    Met à jour un utilisateur. Accessible à l'utilisateur lui-même ou aux administrateurs.
    """
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)


    if current_user_id != utilisateur_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    utilisateur = Utilisateur.query.get(utilisateur_id)
    if not utilisateur:
        return jsonify({"error": "Utilisateur not found"}), 404
    
    if 'mot_de_passe' in data:
        data['mot_de_passe'] = generate_password_hash(data['mot_de_passe'])

    if 'photo' in data:
       utilisateur.photo = data['photo']

    if 'type_compte' in data and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized to change account type"}), 403
    
    for key, value in data.items():
        if hasattr(utilisateur, key):
       
            if key == 'type_compte' and isinstance(value, str):
                try:
                    value = TypeCompteEnum(value)
                except ValueError:
                    return jsonify({"error": "Invalid type_compte value"}), 400
            setattr(utilisateur, key, value)
    
    try:
        db.session.commit()
        return jsonify({"message": "Utilisateur updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

def delete_utilisateur(utilisateur_id):
   
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized"}), 403

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
