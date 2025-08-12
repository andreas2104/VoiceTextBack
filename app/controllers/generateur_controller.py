from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.contenu import Contenu, TypeContenuEnum
from app.models.prompt import Prompt
from app.models.modelIA import ModelIA
from app.models.template import Template
from datetime import datetime
from gpt4all import GPT4All
import requests
import os

bp_ai = Blueprint("bp_ai", __name__)

# Cache du modèle local (pour éviter de le recharger à chaque appel)
_gpt4all_instance = None

def get_gpt4all_instance(model_name):
    global _gpt4all_instance
    if _gpt4all_instance is None:
        _gpt4all_instance = GPT4All(model_name=model_name)
    return _gpt4all_instance

def detect_content_type(model: ModelIA, prompt_text: str):
    if hasattr(model, "modalite"):
        modalite = model.modalite.lower()
        if modalite in ["image", "vision"]:
            return TypeContenuEnum.image
        elif modalite in ["text", "texte"]:
            return TypeContenuEnum.text
    
    # Détection via mots-clés
    keywords_image = ["image", "photo", "dessin", "illustration", "art"]
    if any(word in prompt_text.lower() for word in keywords_image):
        return TypeContenuEnum.image
    
    return TypeContenuEnum.text

def get_api_key(fournisseur: str):
    match fournisseur.lower():
        case "gpt":
            return os.getenv("API_KEY_GPT")
        case "groq":
            return os.getenv("API_KEY_GROQ")
        case "deepseek":
            return os.getenv("API_KEY_DEEPSEEK")
        case "openrouter":
            return os.getenv("API_KEY_OPEN_ROUTER")
        case "gemini":
            return os.getenv("API_KEY_GEMINI")
        case "ollama" | "gpt4all":
            return None  # Pas de clé API nécessaire pour ces fournisseurs
        case _:
            return None

def call_model_api_local(model, prompt_text, params):
    gpt = get_gpt4all_instance(model.nom_model)

    response = gpt.generate(
        prompt=prompt_text,
        n_predict=params.get("max_tokens", 100),
        temperature=params.get("temperature", 0.7)
    )
    return {"type":"text", "content": response}

def call_model_api(model: ModelIA, prompt_text: str, params: dict):
    fournisseur = model.fournisseur.lower()

    if fournisseur == "gpt4all":
        return call_model_api_local(model, prompt_text, params)

 
    headers = {"Content-Type": "application/json"}
    if fournisseur != "ollama" and params.get("api_key"):
        headers["Authorization"] = f"Bearer {params['api_key']}"

    payload = {}
    if fournisseur == "ollama":
        payload = {
            "model": model.parametres_default.get("model", model.nom_model),
            "prompt": prompt_text,
            "stream": False,
            "temperature": params.get("temperature", 0.7)
        }
    elif fournisseur in ["openrouter", "gpt", "groq", "deepseek"]:
        payload = {
            "model": model.parametres_default.get("model", model.nom_model),
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 100)
        }
    elif fournisseur == "gemini":
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": params.get("temperature", 0.7),
                "maxOutputTokens": params.get("max_tokens", 100)
            }
        }
    else:
        return {"type": "error", "content": f"Fournisseur inconnu : {fournisseur}"}

    try:
        timeout_value = 400 if fournisseur == "ollama" else 60
        response = requests.post(model.api_endpoint, headers=headers, json=payload, timeout=timeout_value)
        response.raise_for_status()
        data = response.json()

        if "url" in data:
            return {"type": "image", "content": data["url"]}
        if "data" in data and isinstance(data["data"], list) and "url" in data["data"][0]:
            return {"type": "image", "content": data["data"][0]["url"]}

        if fournisseur == "ollama":
            return {"type": "text", "content": data.get("message", {}).get("content") or data.get("response")}
        elif fournisseur in ["openrouter", "gpt", "groq", "deepseek"]:
            return {"type": "text", "content": data["choices"][0]["message"]["content"]}
        elif fournisseur == "gemini":
            return {"type": "text", "content": data["candidates"][0]["content"]["parts"][0]["text"]}
        else:
            return {"type": "text", "content": data.get("text") or str(data)}

    except Exception as e:
        return {"type": "error", "content": f"Client error: {str(e)}"}

@bp_ai.route("/generer", methods=["POST"])
def generer_contenu():
    data = request.get_json()
    required_fields = ["id_utilisateur", "id_prompt", "id_model"]
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
        if model.fournisseur.lower() not in ["ollama", "gpt4all"] and not api_key:
            return jsonify({"error": f"Clé API non trouvée pour le fournisseur '{model.fournisseur}'"}), 400

        type_contenu_detecte = detect_content_type(model, prompt_text)

        resultat = call_model_api(model, prompt_text, {
            "api_key": api_key,
            "temperature": prompt.parametres.get("temperature", 0.7) if prompt.parametres else 0.7,
            "max_tokens": prompt.parametres.get("max_tokens", 100) if prompt.parametres else 100
        })

        if resultat["type"] == "error":
            return jsonify({"error": resultat["content"]}), 400

        nouveau_contenu = Contenu(
            id_utilisateur=id_utilisateur,
            id_prompt=id_prompt,
            id_model=id_model,
            id_template=id_template,
            titre=data.get("titre", "Contenu généré"),
            type_contenu=type_contenu_detecte,
            texte=resultat["content"] if type_contenu_detecte == TypeContenuEnum.text else None,
            image_url=resultat["content"] if type_contenu_detecte == TypeContenuEnum.image else None,
            meta={"source": model.nom_model, "date": str(datetime.utcnow())}
        )

        db.session.add(nouveau_contenu)
        db.session.commit()

        return jsonify({
            "message": "Contenu généré avec succès",
            "contenu": resultat["content"],
            "type": type_contenu_detecte.value
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
