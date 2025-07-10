from flask import request, jsonify
from app.models.projet import Projet,TypeStatusEnum
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import json



def get_all_projet():
    try:
        projets = Projet.query.all()
        projets_data = [{
            'id': projet.id,
            'id_utilisateur': projet.id_utilisateur,
            'nom_projet': projet.nom_projet,
            'description': projet.description,
            'date_creation': projet.date_creation.isoformat(),
            'date_modification':projet.date_modification.isoformat() if projet.date_modification else None,
            'status': projet.status.value,
            'configuration':projet.configuration
        } for projet in projets]
        return jsonify(projets_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_projet_by_id(projet_id):
    projet = Projet.query.get(projet_id)
    if not projet:
        return jsonify({"error":"projet not found"}),404
    
    return jsonify({
        'id': projet.id,
        'id_utilisateur': projet.id_utilisateur,
        'nom_projet': projet.nom_projet,
        'description': projet.description,
        'date_creation': projet.date_creation.isoformat(),
        'date_modification': projet.date_modification.isoformat() if projet.date_modification else None,
        'status': projet.status.value,
        'configuration': projet.configuration
    }), 200

def create_projet():
    data = request.get_json()
    required_fields = ['id_utilisateur', 'nom_projet', 'description', 'configuration']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:

        configuration = data.get('configuration')
        if isinstance(configuration, str):
            try:
                configuration = json.loads(configuration)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON format for configuration"}), 400
            
        status = TypeStatusEnum.draft
        if 'status' in data:
            try:
                status = TypeStatusEnum(data['status'])
            except ValueError:
                return jsonify({"error": "Invalid status value"}), 400

        new_projet = Projet(
            id_utilisateur=data["id_utilisateur"],
            nom_projet=data['nom_projet'],
            description=data['description'],
            status=status,
            configuration=data.get('configuration'),
            date_modification=None  
        )

        db.session.add(new_projet)
        db.session.commit()
        return jsonify({
            "message": "projet created successfully",
            "projet_id": new_projet.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    

def update_projet(projet_id):
    projet = Projet.query.get(projet_id)
    if not projet:
        return jsonify({"error": "projet not found"}), 404
    
    data = request.get_json()
    try:
        projet.nom_projet = data.get('nom_projet', projet.nom_projet)
        projet.description = data.get('description', projet.description)
        projet.date_modification = datetime.utcnow()
        projet.status = TypeStatusEnum(data.get('status', projet.status))
        projet.configuration = data.get('configuration', projet.configuration)
        projet.id_utilisateur = data.get('id_utilisateur', projet.id_utilisateur)

        db.session.commit()
        return jsonify({
            "message": "projet updated successfully",
            "projet_id": projet.id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    

def delete_projet(projet_id):
        projet = Projet.query.get_or_404(projet_id)   

        try:
            db.session.delete(projet)
            db.session.commit()
            return jsonify({"message": "projet deleted successfully"}), 200                                     
        except Exception as e:  
            db.session.rollback()
            return jsonify({"error": str(e)}), 400


