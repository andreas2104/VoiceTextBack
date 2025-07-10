from flask import request, jsonify
from app.models.modelIA import ModelIA, TypeModelEnum
from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError
import json



def get_all_modelIA():
  try: 
    models = ModelIA.query.all()
    models_data = [{
        'id': modelIA.id,
        'nom_model': modelIA.nom_model,
        'type_model': modelIA.type_model.value,
        'fournisseur':modelIA.fournisseur,
        'api_endpoint': modelIA.api_endpoint,
        'parametres_default': modelIA.parametres_default,
        'cout_par_token': modelIA.cout_par_token,
        'actif': modelIA.actif
    } for modelIA in models]
    return jsonify(models_data), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500
  

def get_modelIA_by_id(modelIA_id):
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
    modelIA = ModelIA.query.get(modelIA_id)
    if not modelIA:
        return jsonify({"error": "ModelIA not found"}), 404
    
    data = request.get_json()
    try:
        modelIA.nom_nodel = data.get('nom_model', modelIA.nom_model)
        modelIA.type_model = data.get('type_model', modelIA.type_model)
        modelIA.fournisseur = data.get('fournisseur', modelIA.fournisseur)
        modelIA.api_endpoint = data.get('api_endpoint', modelIA.api_endpoint)
        modelIA.parametres_default = data.get('parametres_default', modelIA.parametes_default)
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