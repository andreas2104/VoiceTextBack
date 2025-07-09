from flask import request, jsonify
from app.models.projet import Projet,TypeStatusEnum
from app.extensions import db
from datetime import datetime

def get_all_projet():
    try:
        projets = Projet.query.all()
        projets_data = [{
            'id': projet.id,
            'id_utilisateur': projet.id_utilisateur,
            'nom_projet': projet.nom_projet,
            'description': projet.description,
            'date_creation': projet.date_creation.isoformat(),
            'date_modification':projet.date_modification.isoformat(),
            'status': projet.status.value,
            'configuration':projet.configuration
        } for projet in projets]
        return jsonify(projets_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_projet_by_id(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    if not projet:
        return jsonify({"error":"projet not found"}),404
    return jsonify({
        'id': projet_id,
        'id_utilisateur': projet.id_utilisateur,
         'description': projet.description,
         'date_creation': projet.date_creation.isoformat(),
         'date_modification':projet.date_modification.isoformat(),
         'status': projet.status.value,
         'configuration':projet.configuration
    }),200

def create_projet(data):
    data = request.get_json()
    required_fields = ['id_utilisateur', 'nom_projet', 'description', 'date_creation', 'configuration']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        new_projet = Projet(
            id_utilisateur=data["id_utilisateur"],
            nom_projet=data['nom_projet'],
            description=['description'],
            date_creation=datetime.utcnow(),
            status=TypeStatusEnum(data.get('status', TypeStatusEnum.draft)),
            configuration=data.get['configuration']
        )
        db.session.add(new_projet)
        db.session.commit()
        return jsonify({
            "message":"projet created successfully",
            "projet_id": new_projet.id
        }),201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400