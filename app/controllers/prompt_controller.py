from flask import request, jsonify
from app.models.prompt import Prompt
from app.extensions import db
from datetime import datetime
import json


def get_all_prompt():
  try: 
    prompts = Prompt.query.all()
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
    p = Prompt.query.get_or_404(prompt_id)
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
         id_utilisateur=data["id_utilisateur"],
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
    p = Prompt.query.get(prompt_id)
    if not p:
       return jsonify({"error": "prompt not found"}), 400

    data = request.get_json()
    try:
       p.nom_utilisateur =  data.get('nom_utilisateur', p.nom_utilisateur)
       p.nom_prompt = data.get('nom_prompt', p.nom_prompt)
       p.text_prompt = data.get('text_prompt', p.text_prompt)
       p.parametres = data.get('parametres', p.parametres)
       p.public = data.get('public', p.public),
       p.utilisation_count= data.get("utilisatin_count", p.utilisation_count)
       p.date_modification = datetime.utcnow()

       db.session.commit()
       return jsonify({
         "message": "prompt update successfully",
         "prompt_id": p.id
         }), 200
    except Exception as e:
       db.session.rollback()
       return jsonify({" error": str(e)}),400
    

def delete_prompt(prompt_id):
   p = Prompt.query.get_or_404(prompt_id)

   try:
      db.session.delete(p)
      db.session.commit()
      return jsonify({"message": "prompt deleted successfully"}), 200
   except Exception as e:
      db.session.rollback()
      return jsonify({"error": str(e)}), 400

       


   