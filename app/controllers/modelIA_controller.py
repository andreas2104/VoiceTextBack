from flask import request, jsonify
from app.models.modelIA import ModelIA, TypeModelEnum
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError
import json
from flask_jwt_extended import get_jwt_identity


def get_all_modelIA():
    try: 
        current_user_id = get_jwt_identity()
        current_user = Utilisateur.query.get(current_user_id)
        
        if not current_user_id:
            return jsonify({"error": "Authentification requise"}), 401
            
        models = ModelIA.query.all()
        models_data = [{
            'id': modelIA.id,
            'nom_model': modelIA.nom_model,
            'type_model': modelIA.type_model.value,
            'fournisseur': modelIA.fournisseur,
            'api_endpoint': modelIA.api_endpoint,
            'parametres_default': modelIA.parametres_default,
            'cout_par_token': modelIA.cout_par_token,
            'actif': modelIA.actif
        } for modelIA in models]
        return jsonify(models_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
  

def get_modelIA_by_id(modelIA_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    
    if not current_user_id:
        return jsonify({"error": "Authentification requise"}), 401
        
    modelIA = ModelIA.query.get(modelIA_id)
    if not modelIA:
        return jsonify({"error": "ModelIA not found"}), 404
    return jsonify({
        'id': modelIA.id,
        'nom_model': modelIA.nom_model,
        'type_model': modelIA.type_model.value,
        'fournisseur': modelIA.fournisseur,
        'api_endpoint': modelIA.api_endpoint,
        'parametres_default': modelIA.parametres_default,
        'cout_par_token': modelIA.cout_par_token,
        'actif': modelIA.actif
    }), 200


def create_modelIA():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized - Admin rights required"}), 403

    data = request.get_json()
    required_fields = ['nom_model', 'type_model', 'fournisseur', 'api_endpoint', 'cout_par_token']
    
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
        
    try:
        try:
            type_model = TypeModelEnum(data['type_model'])
        except ValueError:
            return jsonify({"error": "Invalid type_model value"}), 400

        new_modelIA = ModelIA(
            nom_model=data['nom_model'],
            type_model=type_model,
            fournisseur=data['fournisseur'],
            api_endpoint=data['api_endpoint'],
            parametres_default=data.get('parametres_default', {}),
            cout_par_token=float(data.get('cout_par_token', 0.0)),
            actif=bool(data.get('actif', True))
        )

        db.session.add(new_modelIA)
        db.session.commit()

        return jsonify({
            "message": "ModelIA created successfully",
            "modelIA_id": new_modelIA.id,
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


def update_modelIA(modelIA_id):
    # Vérifier que l'utilisateur est admin
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized - Admin rights required"}), 403

    modelIA = ModelIA.query.get(modelIA_id)
    if not modelIA:
        return jsonify({"error": "ModelIA not found"}), 404
    
    data = request.get_json()
    try:
        # Correction du nom de l'attribut (nom_nodel -> nom_model)
        modelIA.nom_model = data.get('nom_model', modelIA.nom_model)
        
        # Gérer le type_model s'il est fourni
        if 'type_model' in data:
            try:
                modelIA.type_model = TypeModelEnum(data['type_model'])
            except ValueError:
                return jsonify({"error": "Invalid type_model value"}), 400
                
        modelIA.fournisseur = data.get('fournisseur', modelIA.fournisseur)
        modelIA.api_endpoint = data.get('api_endpoint', modelIA.api_endpoint)
        modelIA.parametres_default = data.get('parametres_default', modelIA.parametres_default)
        modelIA.cout_par_token = data.get('cout_par_token', modelIA.cout_par_token)
        modelIA.actif = data.get('actif', modelIA.actif)

        db.session.commit()
        return jsonify({
            "message": "ModelIA updated successfully",
            "modelIA_id": modelIA.id
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500     
    

def delete_modelIA(modelIA_id):
    # Vérifier que l'utilisateur est admin
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized - Admin rights required"}), 403

    modelIA = ModelIA.query.get(modelIA_id)
    if not modelIA:
        return jsonify({"error": "ModelIA not found"}), 404
    
    try:
        db.session.delete(modelIA)
        db.session.commit()
        return jsonify({"message": "ModelIA deleted successfully"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# Fonctions supplémentaires pour la gestion des modèles

def toggle_model_activation(modelIA_id):
    """Activer/désactiver un modèle IA"""
    # Vérifier que l'utilisateur est admin
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized - Admin rights required"}), 403

    modelIA = ModelIA.query.get(modelIA_id)
    if not modelIA:
        return jsonify({"error": "ModelIA not found"}), 404
    
    try:
        modelIA.actif = not modelIA.actif
        db.session.commit()
        
        status = "activé" if modelIA.actif else "désactivé"
        return jsonify({
            "message": f"ModelIA {status} successfully",
            "modelIA_id": modelIA.id,
            "actif": modelIA.actif
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


def get_active_models():
    """Récupérer uniquement les modèles actifs (accessible à tous les utilisateurs authentifiés)"""
    try:
        # Vérifier que l'utilisateur est authentifié
        current_user_id = get_jwt_identity()
        current_user = Utilisateur.query.get(current_user_id)
        
        if not current_user_id:
            return jsonify({"error": "Authentification requise"}), 401
            
        models = ModelIA.query.filter_by(actif=True).all()
        models_data = [{
            'id': modelIA.id,
            'nom_model': modelIA.nom_model,
            'type_model': modelIA.type_model.value,
            'fournisseur': modelIA.fournisseur,
            'api_endpoint': modelIA.api_endpoint,
            'parametres_default': modelIA.parametres_default,
            'cout_par_token': modelIA.cout_par_token
        } for modelIA in models]
        return jsonify(models_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_models_stats():
    """Statistiques sur les modèles (admin seulement)"""
    # Vérifier que l'utilisateur est admin
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user or current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Unauthorized - Admin rights required"}), 403

    try:
        total_models = ModelIA.query.count()
        active_models = ModelIA.query.filter_by(actif=True).count()
        text_models = ModelIA.query.filter_by(type_model=TypeModelEnum.TEXTE).count()
        image_models = ModelIA.query.filter_by(type_model=TypeModelEnum.IMAGE).count()
        
        # Modèles par fournisseur
        from sqlalchemy import func
        providers = db.session.query(
            ModelIA.fournisseur, 
            func.count(ModelIA.id)
        ).group_by(ModelIA.fournisseur).all()
        
        providers_stats = {provider: count for provider, count in providers}
        
        return jsonify({
            "total_models": total_models,
            "active_models": active_models,
            "text_models": text_models,
            "image_models": image_models,
            "providers": providers_stats
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500