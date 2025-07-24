import os
from flask import Blueprint, request, jsonify
from app.models.modelIA import ModelIA
from app.models.prompt import Prompt
from app.models.contenu import Contenu
from app.extensions import db
import openai
from datetime import datetime

generate_bp = Blueprint("generate", __name__)


def generer_contenu():
    try:
        data = request.get_json()
        id_model = data.get("id_model")     
        id_prompt = data.get("id_prompt")   
        utilisateur_id = data.get("utilisateur_id")  
        titre = data.get("titre") or "Contenu généré"

        if not all([id_model, id_prompt, utilisateur_id]):
            return jsonify({"error": "Champs manquants"}), 400

        model = ModelIA.query.get(id_model)
        if not model:
            return jsonify({"error": "Modèle IA non trouvé"}), 404

        prompt = Prompt.query.get(id_prompt)
        if not prompt:
            return jsonify({"error": "Prompt non trouvé"}), 404

        # Sécurité : clé stockée dans .env
        openai.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_base = model.api_endpoint

        # Appel OpenAI
        completion = openai.ChatCompletion.create(
            model=model.nom_model,
            messages=[
                {"role": "user", "content": prompt.texte_prompt}
            ],
            temperature=prompt.parametres.get("temperature", 0.7),
            max_tokens=prompt.parametres.get("max_tokens", 500)
        )

        texte_genere = completion.choices[0].message.content

        nouveau_contenu = Contenu(
            id_utilisateur=utilisateur_id,
            id_modele=model.id,
            titre=titre,
            texte=texte_genere,
            type_contenu='text',
            meta={"source": "api", "prompt_id": prompt.id},
            date_creation=datetime.utcnow()
        )

        db.session.add(nouveau_contenu)
        db.session.commit()

        return jsonify({
            "message": "Contenu généré avec succès",
            "contenu": {
                "id": nouveau_contenu.id_contenu,
                "titre": titre,
                "texte": texte_genere
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
