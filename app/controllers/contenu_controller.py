from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.contenu import Contenu, TypeContenuEnum
from app.models.prompt import Prompt
from app.models.modelIA import ModelIA
from app.models.template import Template
from datetime import datetime
import requests
import os


def get_api_key(fournisseur: str):
    match fournisseur.lower():
        case "gpt":
            return os.getenv("API_KEY_GPT")
        case "groq":
            return os.getenv("API_KEY_GROQ")
        case "deepseek":
            return os.getenv("API_KEY_DEEPSEEK")
        case "ollama":
            return os.getenv("API_KEY_OLLAMA")
        case "openrouter":
            return os.getenv("API_KEY_OPEN_ROUTER")
        case _:
            return None


def call_model_api(model: ModelIA, prompt_text: str, params: dict = {}):
    headers = {
        "Authorization": f"Bearer {params.get('api_key')}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt_text,
        "max_tokens": params.get("max_tokens", 100),
        "temperature": params.get("temperature", 0.7)
    }

    if model.fournisseur.lower() == "ollama":
        payload = {
            "model":model.parametres_default.get("model",model.nom_model),
            "prompt": prompt_text,
            "stream": False,
            "temperature": params.get("temperature", 0.7)
        }
    elif model.fournisseur.lower() == "openrouter":
        payload = {
             "model": model.parametres_default.get("model", model.nom_model),
            "messages": [
                {"role": "user", "content": prompt_text}
            ],
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 100)
        }
    try:
        response = requests.post(model.api_endpoint, headers=headers, json=payload)
        response.raise_for_status()

        if model.fournisseur.lower() == "ollama":
            return response.json().get("response")
        elif model.fournisseur.lower() == "openrouter":
            return response.json()["choices"][0]["message"]["content"]
        else:
          return response.json().get("text") or response.json()  
    except Exception as e:
        return str(e)


def generer_contenu():
    data = request.get_json()
    required_fields =  ["id_utilisateur", "id_prompt", "id_model"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Champs manquant: {', '.join(missing_fields)}"}), 400


    try:
        id_utilisateur = data["id_utilisateur"]
        id_prompt = data["id_prompt"]
        id_model = data["id_model"]
        id_template = data.get("id_template")

        prompt = Prompt.query.get(id_prompt)
        model = ModelIA.query.get(id_model)
        template = Template.query.get(id_template) if id_template else None

        if not prompt or not model:
            return jsonify({"message": "Prompt ou modèle non trouvé"}), 404

        
        prompt_text = prompt.texte_prompt
        if template:
            prompt_text = template.structure.replace("{{prompt}}", prompt.texte_prompt)

        
        api_key = get_api_key(model.fournisseur)
        if not api_key:
            return jsonify({"error": f"Clé API non trouvée pour le fournisseur '{model.fournisseur}'"}), 400

       
        resultat = call_model_api(model, prompt_text, {
            "api_key": api_key,
            "temperature": prompt.parametres.get("temperature", 0.7) if prompt.parametres else 0.7,
            "max_tokens": prompt.parametres.get("max_tokens", 100) if prompt.parametres else 100
        })

        if "Client error " in resultat:
            return jsonify({"error": resultat}), 400

        
        nouveau_contenu = Contenu(
            id_utilisateur=id_utilisateur,
            id_prompt=id_prompt,
            id_model=id_model,
            id_template=id_template,
            titre=data.get("titre", "Contenu généré"),
            type_contenu=TypeContenuEnum.text,
            texte=resultat,
            meta={"source": model.nom_model, "date": str(datetime.utcnow())}
        )

        db.session.add(nouveau_contenu)
        db.session.commit()

        return jsonify({"message": "Contenu généré avec succès", "contenu": resultat}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
