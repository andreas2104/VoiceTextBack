from flask import request, jsonify
from app.models.template import Template
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

def get_all_template():
    try:
        current_user_id = get_jwt_identity()
        current_user = Utilisateur.query.get(current_user_id)

        if not current_user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        if current_user.type_compte == TypeCompteEnum.admin:
            templates = Template.query.all()
        else:
            templates = Template.query.filter(
                (Template.public == True) | (Template.id_utilisateur == current_user_id)
            ).all()

        templates_data = [t.to_dict() for t in templates]
        return jsonify(templates_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_template_by_id(template_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    t = Template.query.get_or_404(template_id)
    
    if (not t.public) and (t.id_utilisateur != current_user_id) and (current_user.type_compte != TypeCompteEnum.admin):
        return jsonify({"error": "unauthorized"}), 403
        
    return jsonify(t.to_dict()), 200


def create_template():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404 
    data = request.json
    required_fields = ['nom_template', 'structure', 'variables', 'type_sortie', 'public']
    if not data or not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        new_template = Template(
            nom_template=data['nom_template'],
            structure=data['structure'],
            variables=data.get('variables'),
            type_sortie=data['type_sortie'],

            public=data.get('public', False),
            id_utilisateur=current_user_id
        )
        db.session.add(new_template)
        db.session.commit()
        return jsonify({
            'message': 'Template created successfully',
            'template_id': new_template.id,
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400



def update_template(template_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.json
    template = Template.query.get_or_404(template_id)
    
    if template.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "unauthorized"}), 403
        
    try:
        if 'nom_template' in data:
            template.nom_template = data['nom_template']
        if 'structure' in data:
            template.structure = data['structure']
        if 'variables' in data:
            template.variables = data['variables']
        if 'type_sortie' in data:
            template.type_sortie = data['type_sortie']
        if 'public' in data:
            template.public = data['public']

        db.session.commit()
        return jsonify({"message": "Template updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400



def delete_template(template_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    template = Template.query.get(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
        
    if template.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({ "error": "unauthorized"}), 403
    
    try:
        db.session.delete(template)
        db.session.commit()
        return jsonify({"message": "Template deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400