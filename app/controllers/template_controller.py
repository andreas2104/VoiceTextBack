from flask import request, jsonify
from app.models.template import Template
from app.extensions import db


def get_all_template():
  try:
    templates = Template.query.all()
    templates_data = [{
      'id': t.id,
      'nom_template' : t.nom_template,
      'structure': t.structure,
      'variables' : t.structure,
      'type_sortie' : t.type_sortie,
      'public' : t.public,
      'date_creation' : t.date_creation.isoformat(),

  }for t in templates ]
    return jsonify(templates_data),200
  except Exception as e:
    return jsonify({"error": 'Template not found'}), 500
  
def get_template_by_id(template_id):
  t = Template.query.get_or_404(template_id)
  return jsonify({
   'id': t.id,
      'nom_template' : t.nom_template,
      'structure': t.structure,
      'variables' : t.variables,
      'type_sortie' : t.type_sortie,
      'public' : t.public,
      'date_creation' : t.date_creation.isoformat(),
}), 200

def create_template():
  data = request.json
  if not data or not all(key in data for key in ['nom_template', 'structure', 'variables','type_sortie','public','date_creation']):
     return {'error': 'Missing required fields'}, 400
  
  try:
    new_template = Template(
      nom_template=data['nom_template'],
      structure=data['structure'],
      variables=data['variables'],
      type_sortie=data['type_sortie'],
      public=data['public'],
      date_creation=data['date_creation']      
    )
    db.session.add(new_template)
    db.session.commit()
    return jsonify({
      'message': 'Template created successfully',
      'template_id': new_template.id,
    }), 201
  except Exception as e:
    db.session.rollback()
    return jsonify({'error': str(e)}),400
  
def update_template(template_id, data):
  template = Template.query.get_or_404(template_id)
  try:
    db.session.commit()
    return jsonify({"message": "template updated successffuly"}), 200
  except Exception as e:
    db.session.rollback()
    return jsonify({"error": str(e)}),400
  
def delete_template(template_id):
  template = Template.query.get(template_id)
  if not template:
    return jsonify({" error": "Template not found"}), 404
  
  try:
    db.session.delete(template)
    db.session.commit()
    return jsonify({"message": "Template deleted successfully"}),200
  except Exception as e:
    db.session.rollback()
    return jsonify({"error": str(e)}), 400
 