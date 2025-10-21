from flask import request, jsonify
from app.extensions import db
from app.models.contenu import Contenu, TypeContenuEnum
from app.models.prompt import Prompt
from app.models.modelIA import ModelIA, TypeModelEnum
from app.models.template import Template
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
from gpt4all import GPT4All
from sqlalchemy.exc import SQLAlchemyError
import requests
import os
import base64


_gpt4all_instance = None

def get_gpt4all_instance():
    global _gpt4all_instance
    if _gpt4all_instance is None:
        model_path = os.path.expanduser("~/.cache/gpt4all/")
        model_file = "orca-mini-3b-gguf2-q4_0.gguf"
        full_path = os.path.join(model_path, model_file)
        
        if not os.path.exists(full_path):
            return {"type": "error", "content": f"Modèle GPT4All non trouvé à {full_path}"}
        
        _gpt4all_instance = GPT4All(
            model_name=model_file,
            model_path=model_path,
            allow_download=False, 
            device='cpu'  
        )
        print(f"✅ Modèle GPT4All chargé : {full_path}")
    return _gpt4all_instance


def get_api_key(fournisseur: str):
    """Récupère la clé API selon le fournisseur"""
    api_keys = {
        "gpt": "API_KEY_OPENAI",
        "gpt3": "API_KEY_OPENAI", 
        "openai": "API_KEY_OPENAI",
        "grok": "API_KEY_GROK",
        "groq": "API_KEY_GROQ",
        "gemini": "API_KEY_GEMINI",
        "deepseek": "API_KEY_DEEPSEEK",
        "openrouter": "API_KEY_OPEN_ROUTER"
    }
    return os.getenv(api_keys.get(fournisseur.lower()))


def prepare_multimodal_content(prompt_text: str, images: list = None):
    """
    Prépare le contenu multimodal pour l'API
    images: liste de dictionnaires avec {url: str} ou {base64: str, mime_type: str}
    """
    content = []
    
    # Ajouter le texte
    if prompt_text:
        content.append({"type": "text", "text": prompt_text})
    
    # Ajouter les images
    if images:
        for img in images:
            if "url" in img:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img["url"]}
                })
            elif "base64" in img:
                mime_type = img.get("mime_type", "image/jpeg")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{img['base64']}"}
                })
    
    return content


def detect_content_type(model: ModelIA, prompt_text: str, has_images: bool = False):
    """Détecte le type de contenu à générer"""
    # Si le modèle est multimodal et qu'il y a des images en entrée
    if model.type_model == TypeModelEnum.multimodal and has_images:
        return TypeContenuEnum.multimodal
    
    # Détection via mots-clés pour images
    keywords_image = ["image", "photo", "dessin", "illustration", "art", "génère une image"]
    if any(word in prompt_text.lower() for word in keywords_image):
        return TypeContenuEnum.image
    
    return TypeContenuEnum.text


def call_gpt4all(prompt_text, temperature=0.7, max_tokens=512):
    """Appel vers GPT4All local (texte uniquement)"""
    try:
        llm = get_gpt4all_instance()
        with llm.chat_session():
            response = llm.generate(prompt_text, max_tokens=max_tokens, temp=temperature)
        return {"type": "text", "content": response}
    except Exception as e:
        return {"type": "error", "content": f"Erreur GPT4All: {str(e)}"}


def call_openai_multimodal(prompt_text, api_key, model_name="gpt-4-vision-preview", 
                           temperature=0.7, max_tokens=512, images=None):
    """Appel vers l'API OpenAI avec support multimodal"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Préparer le contenu multimodal
    content = prepare_multimodal_content(prompt_text, images)
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": content}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        return {"type": "text", "content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"type": "error", "content": f"Erreur OpenAI Multimodal: {str(e)}"}


def call_openai_api(prompt_text, api_key, model_name="gpt-3.5-turbo", 
                    temperature=0.7, max_tokens=512):
    """Appel vers l'API OpenAI (texte uniquement)"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return {"type": "text", "content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"type": "error", "content": f"Erreur OpenAI: {str(e)}"}


def call_gemini_multimodal(prompt_text, api_key, model_name="gemini-pro-vision",
                           temperature=0.7, max_tokens=512, images=None):
    """Appel vers l'API Gemini avec support multimodal"""
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Préparer les parties du contenu
    parts = [{"text": prompt_text}]
    
    if images:
        for img in images:
            if "base64" in img:
                parts.append({
                    "inline_data": {
                        "mime_type": img.get("mime_type", "image/jpeg"),
                        "data": img["base64"]
                    }
                })
            elif "url" in img:
                # Gemini nécessite base64, donc télécharger l'image
                try:
                    img_response = requests.get(img["url"], timeout=30)
                    img_response.raise_for_status()
                    img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                    parts.append({
                        "inline_data": {
                            "mime_type": img_response.headers.get("content-type", "image/jpeg"),
                            "data": img_base64
                        }
                    })
                except Exception as e:
                    print(f"Erreur téléchargement image: {e}")
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        return {"type": "text", "content": data["candidates"][0]["content"]["parts"][0]["text"]}
    except Exception as e:
        return {"type": "error", "content": f"Erreur Gemini: {str(e)}"}


def call_grok(prompt_text, api_key, temperature=0.7, max_tokens=512):
    """Appel vers l'API Grok"""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return {"type": "text", "content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"type": "error", "content": f"Erreur Grok: {str(e)}"}


def call_model_api(model: ModelIA, prompt_text: str, temperature: float, 
                   max_tokens: int, images: list = None):
    """Appel vers l'API du modèle selon le fournisseur"""
    fournisseur = model.fournisseur.lower()
    
    if fournisseur == "gpt4all":
        if images:
            return {"type": "error", "content": "GPT4All ne supporte pas les images"}
        return call_gpt4all(prompt_text, temperature, max_tokens)
    
    # Récupération de la clé API
    api_key = get_api_key(fournisseur)
    if not api_key:
        return {"type": "error", "content": f"Clé API manquante pour {fournisseur}"}
    
    # Appels multimodaux si images présentes
    if images and model.type_model == TypeModelEnum.multimodal:
        if fournisseur in ["gpt", "openai"]:
            return call_openai_multimodal(prompt_text, api_key, model.nom_model, 
                                         temperature, max_tokens, images)
        elif fournisseur == "gemini":
            return call_gemini_multimodal(prompt_text, api_key, model.nom_model,
                                         temperature, max_tokens, images)
        else:
            return {"type": "error", "content": f"Multimodal non supporté pour {fournisseur}"}
    
    # Appels texte uniquement
    if fournisseur in ["gpt", "gpt3", "openai"]:
        return call_openai_api(prompt_text, api_key, model.nom_model, temperature, max_tokens)
    elif fournisseur == "grok":
        return call_grok(prompt_text, api_key, temperature, max_tokens)
    else:
        return {"type": "error", "content": f"Fournisseur non supporté: {fournisseur}"}


def generer_contenu():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.get_json()
    required = ["id_prompt", "id_model"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Champs manquants: {', '.join(missing)}"}), 400

    try:
        prompt = Prompt.query.get(data["id_prompt"])
        model = ModelIA.query.get(data["id_model"])
        template = Template.query.get(data.get("id_template")) if data.get("id_template") else None

        if not prompt or not model:
            return jsonify({"error": "Prompt ou modèle introuvable"}), 404

        prompt_text = prompt.texte_prompt
        if template:
            prompt_text = template.structure.replace("{{prompt}}", prompt_text)

        temperature = (prompt.parametres or {}).get("temperature") or model.parametres_default.get("temperature", 0.7)
        max_tokens = (prompt.parametres or {}).get("max_tokens") or model.parametres_default.get("max_tokens", 512)

        # NOUVEAU : Récupérer les images si présentes
        images = data.get("images", [])
        # Format attendu: [{"url": "..."}, {"base64": "...", "mime_type": "image/jpeg"}]
        
        has_images = len(images) > 0
        type_contenu = detect_content_type(model, prompt_text, has_images)

        # Appel du modèle avec images
        resultat = call_model_api(model, prompt_text, temperature, max_tokens, images)

        if resultat["type"] == "error":
            return jsonify({"error": resultat["content"]}), 500

        # NOUVEAU : Structure pour contenu multimodal
        contenu_structure = None
        if type_contenu == TypeContenuEnum.multimodal:
            contenu_structure = {
                "blocs": [
                    {"type": "text", "contenu": prompt_text, "role": "input"}
                ]
            }
            # Ajouter les images d'entrée
            for idx, img in enumerate(images):
                contenu_structure["blocs"].append({
                    "type": "image",
                    "url": img.get("url"),
                    "description": f"Image {idx + 1}",
                    "role": "input"
                })
            # Ajouter la réponse du modèle
            contenu_structure["blocs"].append({
                "type": "text",
                "contenu": resultat["content"],
                "role": "output"
            })

        contenu = Contenu(
            id_utilisateur=current_user.id,
            id_prompt=data["id_prompt"],
            id_model=data["id_model"],
            id_template=data.get("id_template"),
            titre=data.get("titre", "Contenu généré"),
            type_contenu=type_contenu,
            texte=resultat["content"] if type_contenu in [TypeContenuEnum.text, TypeContenuEnum.multimodal] else None,
            image_url=resultat["content"] if type_contenu == TypeContenuEnum.image else None,
            contenu_structure=contenu_structure,  # NOUVEAU
            meta={
                "source": model.nom_model,
                "date": str(datetime.utcnow()),
                "has_images": has_images,
                "image_count": len(images)
            }
        )
        
        db.session.add(contenu)
        db.session.commit()

        return jsonify({
            "message": "Contenu généré avec succès",
            "contenu": resultat["content"],
            "type": type_contenu.value,
            "id": contenu.id,
            "structure": contenu_structure
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def get_all_contenus():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if current_user.type_compte == TypeCompteEnum.admin:
        contenus = Contenu.query.all()
    else:
        contenus = Contenu.query.filter_by(id_utilisateur=current_user_id).all()

    data = [{
        "id": c.id,
        "id_utilisateur": c.id_utilisateur,
        "id_projet": c.id_projet,
        "id_prompt": c.id_prompt,
        "id_model": c.id_model,
        "id_template": c.id_template,
        "titre": c.titre,
        "type_contenu": c.type_contenu.value,
        "texte": c.texte,
        "image_url": c.image_url,
        "contenu_structure": c.contenu_structure,  # NOUVEAU
        "meta": c.meta,
        "date_creation": c.date_creation.isoformat()
    } for c in contenus]
    
    return jsonify(data), 200


def get_contenu_by_id(contenu_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
        
    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404
        
    if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    return jsonify({
        "id": contenu.id,
        "id_utilisateur": contenu.id_utilisateur,
        "id_projet": contenu.id_projet,
        "id_prompt": contenu.id_prompt,
        "id_model": contenu.id_model,
        "id_template": contenu.id_template,
        "titre": contenu.titre,
        "type_contenu": contenu.type_contenu.value,
        "texte": contenu.texte,
        "image_url": contenu.image_url,
        "contenu_structure": contenu.contenu_structure,  # NOUVEAU
        "meta": contenu.meta,
        "date_creation": contenu.date_creation.isoformat()
    }), 200


def update_contenu(contenu_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404
        
    if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    data = request.get_json()
    try:
        if "titre" in data:
            contenu.titre = data["titre"]
        if "texte" in data:
            contenu.texte = data["texte"]
        if "image_url" in data:
            contenu.image_url = data["image_url"]
        if "contenu_structure" in data:  # NOUVEAU
            contenu.contenu_structure = data["contenu_structure"]
        if "meta" in data:
            contenu.meta = data["meta"]
            
        db.session.commit()
        return jsonify({"message": "Contenu mis à jour avec succès", "contenu_id": contenu.id}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500


def delete_contenu(contenu_id):
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404
        
    if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403
    
    try:
        db.session.delete(contenu)
        db.session.commit()
        return jsonify({"message": "Contenu supprimé avec succès"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500