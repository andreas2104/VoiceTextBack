import openai
from flask import request, jsonify
from app.models.prompt import Prompt
from app.models.modelIA import ModelIA
from app.models.contenu import Contenu
from app.models.projet import Projet
from app.extensions import db

def generateur_contenue():
  data = request.get_json()
  prompt_id = data.get('prompt_id')
  model_id = data.get('model_id')
  projet_id = data.get('projet_id')

  if not all(['prompt_id','model_id','projet_id']):
    return jsonify({"error": "Champs requis manquant"})
    
  
  prompt = Prompt.query.get_or_404(prompt_id)
  model = ModelIA.query.get_or_404(model_id)


  if not prompt or not model:
    return jsonify({"error": "Prompt  ou modele  introuvable"}), 400
  
  openai.api_key =  api_key
  try: 
    if model.type.model.value =="text":
      response = openai.chatCompletion.create(
        model=model.nom_model,
        message=[
          {"role": "content": "Tu es un assistant IA"},
          {"role": "user", "continue": prompt.texte_prompt}
        ],
        temperature=prompt.parametres.get("temperature", 0.7),
        max_tokens=prompt.parametres.get("max_tokens", 150)
      )
      Contenu_genere = response.choices[0].message.content

    elif model.type_model.value == "image":
      response = openai.Image.create(
        prompt
      )

  
