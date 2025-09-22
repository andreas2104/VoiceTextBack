from flask import request, jsonify
from app.models.prompt import Prompt
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.extensions import db
from datetime import datetime
import json
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError


def get_user():
   current_user_id = get_jwt_identity()
   current_user = Utilisateur.query.get(current_user_id)
   if not current_user:
      return None, jsonify({"error": "Utilisateur non trouver"}), 404
   return current_user, None, None


def get_all_prompt():
  try: 
    current_user, error_response, status_code = get_user()
    if error_response:
       return error_response, status_code
    if current_user.type_compte == TypeCompteEnum.admin:
       
      prompts = Prompt.query.all()
    else:
      prompts = Prompt.query.filter(
         (Prompt.public == True) | (Prompt.id_utilisateur == current_user.id)
      ).all()
    p_data = [{
      'id':p.id,
      'id_utilisateur': p.id_utilisateur,
      'nom_prompt': p.nom_prompt,
      'texte_prompt': p.texte_prompt,
      'parametres': p.parametres,
      'public': p.public,
      'utilisation_count': p.utilisation_count,   
      'date_creation': p.date_creation.isoformat() if p.date_creation else None,
      'date_modification': p.date_modification.isoformat() if p.date_modification else None
    } for p in prompts]
    return jsonify(p_data), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500
  

def get_prompt_by_id(prompt_id):
      current_user, error_response, status_code = get_user()
      if error_response:
         return error_response, status_code
      
      p = Prompt.query.get_or_404(prompt_id)
      if not p.public and p.id_utilisateur != current_user.id and current_user.type_compte != TypeCompteEnum.admin:
         return jsonify({"error": "non authorise"}), 403
      
      return jsonify({
      'id': p.id,
      'id_utilisateur': p.id_utilisateur,
      'nom_prompt': p.nom_prompt,
      'texte_prompt': p.texte_prompt,
      'paramatres': p.parametres,
      'public': p.public,
      'utilisation_count': p.utilisation_count,
      'date_creation': p.date_creation,
      'date_modification': p.date_modification.isoformat() if p.date_modification else None
    }), 200


def create_prompt():
   current_user, error_response, status_code = get_user()
   if error_response:
      return error_response, status_code
   data = request.get_json()
   required_fields = ['id_utilisateur','nom_prompt','parametres','public','utilisation_count']
   if not data or not all(field in data for field in required_fields ):
      return jsonify({"error": 'missing required fields'}), 400
   
   try: 
      parametres = data.get('parametres')
      if isinstance(parametres, str):
         try: 
            parametres = json.loads(parametres)
         except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format for paramatres"}), 400
      new_prompt = Prompt(
         id_utilisateur=current_user.id,
         nom_prompt=data["nom_prompt"],
         texte_prompt=data["texte_prompt"],
         parametres=data["parametres"],
         public=data["public"],
         utilisation_count=data.get("utilisation_count",0),
         date_modification=None
      )     

      db.session.add(new_prompt)
      db.session.commit()
      return jsonify({
         "message": "prompt created successfully",
         "prompt_id": new_prompt.id
      }), 201
   except Exception as e:
      db.session.rollback()
      return jsonify({"error": str(e)}), 400
   

def update_prompt(prompt_id):
    current_user, error_response, status_code = get_user()
    if error_response:
        return error_response, status_code

    p = Prompt.query.get_or_404(prompt_id)

    if p.id_utilisateur != current_user.id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "non authorise"}), 403

    data = request.get_json()
    try:
        p.nom_prompt = data.get('nom_prompt', p.nom_prompt)
        p.texte_prompt = data.get('texte_prompt', p.texte_prompt)  
        p.parametres = data.get('parametres', p.parametres)
        p.public = data.get('public', p.public)                    
        p.utilisation_count = data.get("utilisation_count", p.utilisation_count) 
        p.date_modification = datetime.utcnow()

        db.session.commit()
        return jsonify({
            "message": "prompt update successfully",
            "prompt_id": p.id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


def delete_prompt(prompt_id):
   current_user, error_response, status_code = get_user()
   if error_response:
        return error_response, status_code
   
   p = Prompt.query.get_or_404(prompt_id)

   if p.id_utilisateur != current_user.id and current_user.type_compte != TypeCompteEnum.admin:
      return jsonify({"error": "non authorise"}), 403
   try:
      db.session.delete(p)
      db.session.commit()
      return jsonify({"message": "prompt deleted successfully"}), 200
   except Exception as e:
      db.session.rollback()
      return jsonify({"error": str(e)}), 400

       


   