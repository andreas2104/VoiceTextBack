from flask import request, jsonify
from app.extensions import db
from app.models.contenu import Contenu, TypeContenuEnum
from app.models.prompt import Prompt
from app.models.modelIA import ModelIA
from app.models.template import Template
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import requests
import os
import re
import time
from typing import Optional


def is_valid_base64_image(content: str) -> bool:
    """Vérifie si le contenu est une image base64 valide"""
    if content.startswith("data:image/"):
        return True
    return len(content) > 100


def extract_image_from_markdown(content: str) -> Optional[str]:
    """Extrait une image base64 depuis un format markdown"""
    patterns = [
        r'!\[.*?\]\((data:image/[^)]+)\)',
        r'\[.*?\]\((data:image/[^)]+)\)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None


def get_api_key(fournisseur: str):
    """Récupère la clé API selon le fournisseur"""
    api_keys = {
        "gpt": "COMET_API_KEY",
        "gemini": "COMET_API_KEY",
        "gemini_flash": "COMET_API_KEY",
    }
    return os.getenv(api_keys.get(fournisseur.lower()))


def prepare_multimodal_content(prompt_text: str, images: list = None):
    """Prépare le payload multimodal pour l'API"""
    content = [{"type": "text", "text": prompt_text}] if prompt_text else []
    
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


def call_gpt_api(prompt_text, api_key, model_name="gpt-3.5-turbo", 
                 temperature=0.7, max_tokens=512):
    url = "https://api.cometapi.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
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


def call_gemini_api(prompt_text, api_key, model_name="gemini-2.0-flash-exp",
                    temperature=0.7, max_tokens=512, images=None):
    """Appel API Gemini via Comet avec retry + détection image"""
    url = 'https://api.cometapi.com/v1/chat/completions'
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    if images and len(images) > 0:
        content = prepare_multimodal_content(prompt_text, images)
        messages = [{"role": "user", "content": content}]
    else:
        messages = [{"role": "user", "content": prompt_text}]
    
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f" Tentative {attempt + 1}/{max_retries} - {model_name}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if not response.text or response.text.strip() == "":
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f" Réponse vide, retry dans {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                return {'type': 'error', 'content': 'Réponse vide de l\'API Gemini'}
            
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Détection d'image markdown
            markdown_image = extract_image_from_markdown(content)
            if markdown_image:
                print(f"Image markdown détectée")
                return {"type": "image", "content": markdown_image}
            
            # Détection data URI
            if content.startswith("data:image/"):
                print(f" Data URI détectée")
                return {"type": "image", "content": content}
            
            # Détection base64 brute
            if len(content) > 50000 and is_valid_base64_image(content):
                print(f"Image base64 brute détectée")
                return {"type": "image", "content": f"data:image/png;base64,{content}"}
            
            # Détection URL d'image
            if content.startswith("http") and any(ext in content.lower() for ext in ['.jpg', '.png', '.jpeg', '.webp', '.gif']):
                print(f" URL d'image détectée")
                return {"type": "image", "content": content}
            
            return {"type": "text", "content": content}
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [503, 429] and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ HTTP {e.response.status_code}, retry dans {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            return {'type': 'error', 'content': f"Erreur Gemini HTTP {e.response.status_code}: {error_text}"}
            
        except ValueError as e:
            print(f"❌ Erreur JSON: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {'type': 'error', 'content': f"Réponse invalide: {response.text[:200]}"}
            
        except Exception as e:
            return {'type': 'error', 'content': f"Erreur Gemini: {str(e)}"}
    
    return {'type': 'error', 'content': "Service Gemini indisponible après 3 tentatives"}


def call_model_api(model, prompt_text: str, temperature: float, max_tokens: int, images: list = None):
    fournisseur = model.fournisseur.lower()
    print(f" Appel: {fournisseur} - {model.nom_model}")

    api_key = get_api_key(fournisseur)
    if not api_key:
        return {"type": "error", "content": f"Clé API manquante pour {fournisseur}"}

    if fournisseur == "gpt":
        return call_gpt_api(prompt_text, api_key, model.nom_model, temperature, max_tokens)
    elif fournisseur in ["gemini", "gemini_flash"]:
        return call_gemini_api(prompt_text, api_key, model.nom_model, temperature, max_tokens, images)
    else:
        return {"type": "error", "content": f"Fournisseur inconnu: {fournisseur}"}


def generer_contenu():
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.get_json()
    
    if not data.get("id_prompt") and not data.get("custom_prompt"):
        return jsonify({"error": "Soit 'id_prompt' soit 'custom_prompt' doit être fourni"}), 400

    required = ["id_model"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Champs manquants: {', '.join(missing)}"}), 400

    try:
        model = ModelIA.query.get(data["id_model"])
        template = Template.query.get(data.get("id_template")) if data.get("id_template") else None

        if not model:
            return jsonify({"error": "Modèle introuvable"}), 404

        prompt_text = ""
        id_prompt_used = None
        prompt_custom_used = None

        if data.get("id_prompt"):
            prompt = Prompt.query.get(data["id_prompt"])
            if not prompt:
                return jsonify({"error": "Prompt introuvable"}), 404
            
            prompt_text = prompt.texte_prompt
            id_prompt_used = data["id_prompt"]
            
            temperature = (prompt.parametres or {}).get("temperature") or model.parametres_default.get("temperature", 0.7)
            max_tokens = (prompt.parametres or {}).get("max_tokens") or model.parametres_default.get("max_tokens", 512)
            
        else:
            prompt_text = data["custom_prompt"]
            prompt_custom_used = data["custom_prompt"]
            
            temperature = model.parametres_default.get("temperature", 0.7)
            max_tokens = model.parametres_default.get("max_tokens", 512)

        if template:
            prompt_text = template.structure.replace("{{prompt}}", prompt_text)

        images = data.get("images", [])
        has_images = len(images) > 0

        resultat = call_model_api(model, prompt_text, temperature, max_tokens, images)
        print(f" Résultat: type={resultat['type']}, taille={len(resultat.get('content', ''))}")

        if resultat["type"] == "error":
            return jsonify({"error": resultat["content"]}), 500

        if resultat["type"] == "image":
            type_contenu = TypeContenuEnum.image
            image_url = resultat["content"] 
            text_content = None
            print(f" IMAGE stockée en base64")
            
        elif resultat["type"] == "text":
            type_contenu = TypeContenuEnum.multimodal if has_images else TypeContenuEnum.text
            text_content = resultat["content"]
            image_url = None
            print(f"{type_contenu.value.upper()}")
        else:
            type_contenu = TypeContenuEnum.text
            text_content = resultat["content"]
            image_url = None

        contenu_structure = None
        if type_contenu == TypeContenuEnum.multimodal:
            contenu_structure = {
                "blocs": [{"type": "text", "contenu": prompt_text, "role": "input"}]
            }
            for idx, img in enumerate(images):
                contenu_structure["blocs"].append({
                    "type": "image",
                    "url": img.get("url"),
                    "description": f"Image {idx + 1}",
                    "role": "input"
                })
            contenu_structure["blocs"].append({
                "type": "text",
                "contenu": resultat["content"],
                "role": "output"
            })

        contenu = Contenu(
            id_utilisateur=current_user.id,
            id_prompt=id_prompt_used,
            custom_prompt=prompt_custom_used,
            id_model=data["id_model"],
            id_template=data.get("id_template"),
            titre=data.get("titre", "Contenu généré"),
            type_contenu=type_contenu,
            texte=text_content if type_contenu in [TypeContenuEnum.text, TypeContenuEnum.multimodal] else None,
            image_url=image_url,  
            contenu_structure=contenu_structure,
            meta={
                "source": model.nom_model,
                "date": str(datetime.utcnow()),
                "has_images": has_images,
                "image_count": len(images),
                "detected_type": resultat["type"]
            }
        )
        
        db.session.add(contenu)
        db.session.commit()

        return jsonify({
            "message": "Contenu généré avec succès",
            "contenu": text_content,
            "type": type_contenu.value,
            "id": contenu.id,
            "structure": contenu_structure,
            "image_url": image_url  
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f" Erreur génération: {str(e)}")
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
        "custom_prompt": c.custom_prompt,
        "id_model": c.id_model,
        "id_template": c.id_template,
        "titre": c.titre,
        "type_contenu": c.type_contenu.value,
        "texte": c.texte,
        "image_url": c.image_url,  # Le base64 sera retourné tel quel
        "contenu_structure": c.contenu_structure,
        "meta": c.meta,
        "date_creation": c.date_creation.isoformat()
    } for c in contenus]
    
    return jsonify(data), 200


def get_contenu_by_id(contenu_id):
    print(f"contenuId: {contenu_id}")
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)
    print(f"current_user: {current_user}")
    print(f'class:{type(current_user.type_compte)} : value {current_user.type_compte}")')
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
        
    contenu = Contenu.query.get(contenu_id)
    if not contenu:
        return jsonify({"error": "Contenu introuvable"}), 404
        
    if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        print(f"current_user.type_compte: {current_user.type_compte}")
        print(f"contenu.id: {contenu.id_utilisateur}, current_user.id: {current_user.id}")
        print(f"class: {type(contenu.id_utilisateur)} vs {type(current_user_id)}")
        return jsonify({"error": "Non autorisé"}), 403

    return jsonify({
        "id": contenu.id,
        "id_utilisateur": contenu.id_utilisateur,
        "id_projet": contenu.id_projet,
        "id_prompt": contenu.id_prompt,
        "custom_prompt": contenu.custom_prompt,
        "id_model": contenu.id_model,
        "id_template": contenu.id_template,
        "titre": contenu.titre,
        "type_contenu": contenu.type_contenu.value,
        "texte": contenu.texte,
        "image_url": contenu.image_url,  
        "contenu_structure": contenu.contenu_structure,
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
        if "contenu_structure" in data:
            contenu.contenu_structure = data["contenu_structure"]
        if "meta" in data:
            contenu.meta = data["meta"]
        if "custom_prompt" in data:
            contenu.custom_prompt = data["custom_prompt"]
        if "id_prompt" in data:
            contenu.id_prompt = data["id_prompt"]
            
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