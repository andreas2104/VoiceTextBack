import os
import requests
from flask import request, jsonify
from app.extensions import db
from app.models.contenu import Contenu, TypeContenuEnum
from app.models.prompt import Prompt
from app.models.modelIA import ModelIA
from app.models.template import Template
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
from gpt4all import GPT4All
from sqlalchemy.exc import SQLAlchemyError


_gpt4all_instance = None
def get_gpt4all_instance():
    global _gpt4all_instance
    if _gpt4all_instance is None:
        model_path = os.path.expanduser("~/.cache/gpt4all/orca-mini-3b-gguf2-q4_0.gguf")
        _gpt4all_instance = GPT4All(
            "orca-mini-3b-gguf2-q4_0.gguf",
            model_path=os.path.dirname(model_path)
        )
        print(f"Modèle GPT4All chargé : {model_path}")
    return _gpt4all_instance


def call_gpt4all(prompt_text, temperature=0.7, max_tokens=512):
    try:
        llm = get_gpt4all_instance()
        with llm.chat_session():
            response = llm.generate(prompt_text, max_tokens=max_tokens, temp=temperature)
        return {"type": "text", "content": response}
    except Exception as e:
        return {"type": "error", "content": f"Erreur GPT4All: {str(e)}"}

def call_gpt3(prompt_text, api_key, temperature=0.7, max_tokens=512):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return {"type": "text", "content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"type": "error", "content": f"Erreur GPT-3: {str(e)}"}

def call_grok(prompt_text, api_key, temperature=0.7, max_tokens=512):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return {"type": "text", "content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"type": "error", "content": f"Erreur Grok: {str(e)}"}


def generer_contenu():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error":"Utiliserateur non trouver"}), 404

    data = request.get_json()
    required = ["id_utilisateur", "id_prompt", "id_model"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Champs manquants: {', '.join(missing)}"}), 400

    try:
        prompt = Prompt.query.get(data["id_prompt"])
        model = ModelIA.query.get(data["id_model"])
        template = Template.query.get(data.get("id_template")) if data.get("id_template") else None

        if not prompt or not model:
            return jsonify({"error": "Prompt ou modèle introuvable"}), 404
        if current_user.type_compte != TypeContenuEnum.admin:
            data["id_utilisateur"] = current_user_id
        else:
            data["id_utilisateur"] = data.get("id_utilisateur", current_user_id)

        prompt_text = prompt.texte_prompt
        if template:
            prompt_text = template.structure.replace("{{prompt}}", prompt_text)

        temperature = (prompt.parametres or {}).get("temperature") or model.parametres_default.get("temperature", 0.7)
        max_tokens = (prompt.parametres or {}).get("max_tokens") or model.parametres_default.get("max_tokens", 512)

        fournisseur = model.fournisseur.lower()
        if fournisseur == "gpt4all":
            resultat = call_gpt4all(prompt_text, temperature, max_tokens)
        elif fournisseur == "gpt3":
            api_key = os.getenv("API_KEY_OPENAI")
            if not api_key:
                return jsonify({"error": "Clé API OpenAI manquante"}), 400
            resultat = call_gpt3(prompt_text, api_key, temperature, max_tokens)
        elif fournisseur == "grok":
            api_key = os.getenv("API_KEY_GROK")
            if not api_key:
                return jsonify({"error": "Clé API Grok manquante"}), 400
            resultat = call_grok(prompt_text, api_key, temperature, max_tokens)
        else:
            return jsonify({"error": f"Fournisseur non supporté: {fournisseur}"}), 400

        if resultat["type"] == "error":
            return jsonify({"error": resultat["content"]}), 500

        contenu = Contenu(
            id_utilisateur=current_user.id,
            id_prompt=data["id_prompt"],
            id_model=data["id_model"],
            id_template=data.get("id_template"),
            titre=data.get("titre", "Contenu généré"),
            type_contenu=TypeContenuEnum.text,
            texte=resultat["content"],
            meta={"source": model.nom_model, "date": str(datetime.utcnow())}
        )
        db.session.add(contenu)
        db.session.commit()

        return jsonify({
            "message": "✅ Contenu généré avec succès",
            "contenu": resultat["content"],
            "type": "text"
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def get_all_contenus():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouver"}), 404
    if current_user.type_compte == TypeCompteEnum.admin:

        contenu = Contenu.query.all()
    else:
        contenu = Contenu.query.filter_by(id_utilisateur=current_user_id).all()

    data = [{
        "id": c.id,
        "id_utilisateur": c.id_utilisateur,
        "id_prompt": c.id_prompt,
        "id_model": c.id_model,
        "id_template": c.id_template,
        "titre": c.titre,
        "type_contenu": c.type_contenu.value,
        "texte": c.texte,
        "image_url": c.image_url,
        "meta": c.meta,
        "date_creation": c.date_creation.isoformat()
    } for c in contenu]
    return jsonify(data), 200


def get_contenu_by_id(contenu_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404
    if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non authorise"}), 403

    return jsonify({
        "id": contenu.id,
        "id_utilisateur": contenu.id_utilisateur,
        "id_prompt": contenu.id_prompt,
        "id_model": contenu.id_model,
        "id_template": contenu.id_template,
        "titre": contenu.titre,
        "type_contenu": contenu.type_contenu.value,
        "texte": contenu.texte,
        "image_url": contenu.image_url,
        "meta": contenu.meta,
        "date_creation": contenu.date_creation.isoformat()
    }), 200


def update_contenu(contenu_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query(current_user_id)
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404
    if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non authorise"}), 403

    data = request.get_json()
    try:
        contenu.titre = data.get("titre", contenu.titre)
        contenu.texte = data.get("texte", contenu.texte)
        contenu.image_url = data.get("image_url", contenu.image_url)
        contenu.meta = data.get("meta", contenu.meta)
        db.session.commit()
        return jsonify({"message": "✅ Contenu mis à jour", "contenu_id": contenu.id}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur DB: {str(e)}"}), 400


def delete_contenu(contenu_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouve"}), 404

    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404 
    if contenu.id_utilisateur != current_user_id and current_user.Type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "unauthorized"}), 403
    
    try:
        db.session.delete(contenu)
        db.session.commit()
        return jsonify({"message": "✅ Contenu supprimé"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur DB: {str(e)}"}), 400
