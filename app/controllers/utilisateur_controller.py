from flask import request, jsonify
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import get_jwt_identity

def get_all_utilisateurs():
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
    try:
        current_user_id = get_jwt_identity()
        current_user = Utilisateur.query.get(current_user_id)
        if not current_user:
            return jsonify({"error": "Utilisateur courant non trouvé"}), 404

        # Vérification : seul l'admin peut modifier un autre utilisateur
        if current_user_id != utilisateur_id and current_user.type_compte != TypeCompteEnum.admin:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.json
        utilisateur = Utilisateur.query.get(utilisateur_id)
        if not utilisateur:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        # Gestion du mot de passe
        if "mot_de_passe" in data and data["mot_de_passe"]:
            utilisateur.mot_de_passe = generate_password_hash(data["mot_de_passe"])

        # Gestion de la photo
        if "photo" in data:
            utilisateur.photo = data["photo"]

        # Gestion du type_compte : seul un admin peut changer le rôle
        if "type_compte" in data:
            if current_user.type_compte != TypeCompteEnum.admin:
                return jsonify({"error": "Unauthorized to change account type"}), 403
            try:
                utilisateur.type_compte = TypeCompteEnum(data["type_compte"])
            except ValueError:
                return jsonify({"error": "Invalid type_compte value"}), 400

        # Autres champs
        for key in ["nom", "prenom", "email", "actif"]:
            if key in data:
                setattr(utilisateur, key, data[key])

        db.session.commit()
        return jsonify({"message": "Utilisateur mis à jour avec succès"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



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

def current_utilisateur():
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "Token invalide"}), 401

        utilisateur = Utilisateur.query.get(current_user_id)
        if not utilisateur:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        utilisateur_data = {
            "id": utilisateur.id,
            "nom": utilisateur.nom,
            "prenom": utilisateur.prenom,
            "email": utilisateur.email,
            "type_compte": utilisateur.type_compte.value if utilisateur.type_compte else None,
            "date_creation": utilisateur.date_creation.isoformat() if utilisateur.date_creation else None,
            "actif": utilisateur.actif,
            "photo": utilisateur.photo
        }

        return jsonify(utilisateur_data), 200
    except Exception as e:
        print("Erreur dans get_current_utilisateur:", e)
        return jsonify({"error": str(e)}), 500
