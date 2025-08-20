from flask import request, jsonify
from app.models.template import Template
from app.extensions import db


def get_all_template():
    try:
        templates = Template.query.all()
        templates_data = [t.to_dict() for t in templates]
        return jsonify(templates_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_template_by_id(template_id):
    t = Template.query.get_or_404(template_id)
    return jsonify(t.to_dict()), 200


def create_template():
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
            public=data['public']
            # date_creation est auto-géré
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
    data = request.json
    template = Template.query.get_or_404(template_id)
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
    template = Template.query.get(template_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404

    try:
        db.session.delete(template)
        db.session.commit()
        return jsonify({"message": "Template deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
