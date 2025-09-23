from flask import request, jsonify
from app.extensions import db
from app.models.plateforme import Plateforme, TypePlateformeEnum, StatutConnexionEnum
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.services.social_media_service import SocialMediaService
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

def connecter_plateforme():
    """Connecte une plateforme sociale (OAuth)"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.get_json()
    required_fields = ["nom_plateforme", "access_token", "nom_compte"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Champs manquants: {', '.join(missing_fields)}"}), 400

    try:
        # Vérifier si la plateforme existe déjà pour cet utilisateur
        existing = Plateforme.query.filter_by(
            id_utilisateur=current_user_id,
            nom_plateforme=TypePlateformeEnum(data["nom_plateforme"])
        ).first()

        if existing:
            # Mettre à jour les tokens
            existing.access_token = data["access_token"]
            existing.refresh_token = data.get("refresh_token")
            existing.token_expiration = datetime.utcnow() + timedelta(days=60)  # Facebook/LinkedIn tokens
            existing.nom_compte = data["nom_compte"]
            existing.id_compte_externe = data.get("id_compte_externe")
            existing.statut_connexion = StatutConnexionEnum.connecte
            existing.date_modification = datetime.utcnow()
            
            plateforme = existing
        else:
            # Créer nouvelle connexion
            plateforme = Plateforme(
                id_utilisateur=current_user_id,
                nom_plateforme=TypePlateformeEnum(data["nom_plateforme"]),
                nom_compte=data["nom_compte"],
                id_compte_externe=data.get("id_compte_externe"),
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_expiration=datetime.utcnow() + timedelta(days=60),
                statut_connexion=StatutConnexionEnum.connecte,
                permissions_accordees=data.get("permissions", []),
                parametres_publication=data.get("parametres_publication", {})
            )
            db.session.add(plateforme)

        # Vérifier le token immédiatement
        token_valide = SocialMediaService.verifier_statut_token(plateforme)
        
        db.session.commit()

        return jsonify({
            "message": "Plateforme connectée avec succès",
            "plateforme": plateforme.to_dict(),
            "token_valide": token_valide
        }), 201

    except ValueError:
        return jsonify({"error": "Type de plateforme non supporté"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500

def publier_contenu():
    """Publie un contenu sur une plateforme"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    required_fields = ["id_plateforme", "id_publication"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Champs manquants: {', '.join(missing_fields)}"}), 400

    try:
        from app.models.publication import Publication
        from app.models.contenu import Contenu
        
        plateforme = Plateforme.query.get(data["id_plateforme"])
        publication = Publication.query.get(data["id_publication"])
        
        if not plateforme or not publication:
            return jsonify({"error": "Plateforme ou publication introuvable"}), 404

        if plateforme.id_utilisateur != current_user_id:
            return jsonify({"error": "Non autorisé"}), 403

        # Récupérer le contenu
        contenu = Contenu.query.get(publication.id_contenu)
        if not contenu:
            return jsonify({"error": "Contenu introuvable"}), 404

        # Publier selon la plateforme
        if plateforme.nom_plateforme == TypePlateformeEnum.facebook:
            result = SocialMediaService.publier_sur_facebook(
                plateforme, publication, contenu.texte, contenu.image_url
            )
        elif plateforme.nom_plateforme == TypePlateformeEnum.linkedin:
            result = SocialMediaService.publier_sur_linkedin(
                plateforme, publication, contenu.texte, contenu.image_url
            )
        else:
            return jsonify({"error": "Plateforme non supportée"}), 400

        if result["success"]:
            return jsonify({
                "message": "Publication réussie",
                "id_externe": result.get("id_externe"),
                "publication": publication.to_dict()
            }), 200
        else:
            return jsonify({"error": result["error"]}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_statistiques_plateforme(plateforme_id):
    """Récupère les statistiques d'une plateforme"""
    current_user_id = get_jwt_identity()
    
    plateforme = Plateforme.query.get(plateforme_id)
    if not plateforme:
        return jsonify({"error": "Plateforme introuvable"}), 404

    if plateforme.id_utilisateur != current_user_id:
        return jsonify({"error": "Non autorisé"}), 403

    # Compter les publications par statut
    from app.models.publication import Publication, StatutPublicationEnum
    
    stats = {
        "publications_totales": Publication.query.filter_by(id_plateforme=plateforme_id).count(),
        "publications_publiees": Publication.query.filter_by(
            id_plateforme=plateforme_id, 
            statut=StatutPublicationEnum.publie
        ).count(),
        "publications_programmees": Publication.query.filter_by(
            id_plateforme=plateforme_id, 
            statut=StatutPublicationEnum.programme
        ).count(),
        "publications_brouillon": Publication.query.filter_by(
            id_plateforme=plateforme_id, 
            statut=StatutPublicationEnum.brouillon
        ).count(),
        "publications_echec": Publication.query.filter_by(
            id_plateforme=plateforme_id, 
            statut=StatutPublicationEnum.echec
        ).count(),
        "posts_aujourd_hui": plateforme.posts_publies_aujourd_hui,
        "limite_quotidienne": plateforme.limite_posts_jour,
        "peut_publier": plateforme.peut_publier_aujourd_hui(),
        "token_valide": plateforme.is_token_valid(),
        "derniere_publication": plateforme.derniere_publication.isoformat() if plateforme.derniere_publication else None
    }

    return jsonify(stats), 200