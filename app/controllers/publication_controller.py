from flask import request, jsonify, current_app
from app.extensions import db
from app.models.publication import Publication, StatutPublicationEnum
from app.models.utilisateur import Utilisateur, TypeCompteEnum, Token
from app.models.contenu import Contenu
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import requests
from app.services.x_service import publish_to_x_api,delete_publication_from_x


def create_publication():
    """Crée une publication immédiate ou programmée, avec publication sur X via x_service."""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.get_json()
    if not data or "id_contenu" not in data:
        return jsonify({"error": "Champ 'id_contenu' manquant"}), 400

    try:
        contenu = Contenu.query.get(data["id_contenu"])
        if not contenu:
            return jsonify({"error": "Contenu introuvable"}), 404
        if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
            return jsonify({"error": "Non autorisé"}), 403
        # texte_contenu = data.get("message") or getattr(contenu, "texte", "") or getattr(contenu, "titre", "") or ""
        texte_contenu = data.get("message") or contenu.texte or contenu.titre or ""
        image_url = data.get("image_url") or contenu.image_url
        
        
        if not texte_contenu:
            return jsonify({"error": "Aucun contenu texte disponible pour la publication"}), 400

        url_media = data.get("image_url") or getattr(contenu, "url_media", None) or getattr(contenu, "image_url", None)

        # Gestion de la planification
        statut = StatutPublicationEnum.brouillon
        date_programmee = None
        publier_maintenant = True

        if data.get("date_programmee"):
            try:
                date_programmee = datetime.fromisoformat(data["date_programmee"].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)

                if date_programmee > now:
                    statut = StatutPublicationEnum.programme
                    publier_maintenant = False
                else:
                    statut = StatutPublicationEnum.publie
                    publier_maintenant = True
                    date_programmee = None
            except ValueError:
                return jsonify({"error": "Format de date invalide"}), 400
        else:
            statut = StatutPublicationEnum.publie

        if data.get("statut") == "brouillon":
            statut = StatutPublicationEnum.brouillon
            publier_maintenant = False

        tweet_id = None
        url_publication = None
        tweet_data = {}

        # Publication immédiate via x_service
        if publier_maintenant:
            token = Token.query.filter_by(utilisateur_id=current_user_id, provider='x').first()
            if not token or not token.is_valid():
                return jsonify({"error": "Token X expiré ou manquant"}), 401

            # Utiliser le texte du contenu correct
            url_publication, tweet_id, result = publish_to_x_api(
                texte_contenu,  
                token.access_token, 
                # url_media 
                image_url
            )

            if not url_publication and "Erreur" in (result or ""):
                # Échec publication → enregistrer l'erreur
                publication = Publication(
                    id_utilisateur=current_user_id,
                    id_contenu=contenu.id,
                    plateforme='x',
                    titre_publication=data.get("titre_publication") or getattr(contenu, "titre", "Sans titre"),
                    statut=StatutPublicationEnum.echec,
                    message_erreur=result,
                )
                db.session.add(publication)
                db.session.commit()
                return jsonify({"error": "Échec de publication sur X", "details": result}), 502

            tweet_data = result or {}

        # Enregistrement en base
        publication = Publication(
            id_utilisateur=current_user_id,
            id_contenu=data["id_contenu"],
            plateforme='x',
            titre_publication=data.get("titre_publication") or getattr(contenu, "titre", f"Publication X - {datetime.utcnow().strftime('%d/%m/%Y')}"),
            statut=statut,
            date_programmee=date_programmee,
            date_publication=datetime.utcnow() if statut == StatutPublicationEnum.publie else None,
            url_publication=url_publication,
            id_externe=tweet_id,
            parametres_publication={
                "tweet_id": tweet_id,
                "api_response": tweet_data,
                "publication_immediate": publier_maintenant,
                "message": texte_contenu,
                 "image_url": image_url    
                # "image_url": url_media     
            }
        )

        db.session.add(publication)

        if statut == StatutPublicationEnum.publie:
            if hasattr(contenu, 'est_publie'):
                contenu.est_publie = True
            if hasattr(contenu, 'date_publication'):
                contenu.date_publication = datetime.utcnow()

        db.session.commit()

        return jsonify({
            "message": "Publication créée avec succès" if publier_maintenant else "Publication programmée avec succès",
            "publication": publication.to_dict()
            #   {
                # "id": publication.id,
                # "titre": publication.titre_publication,
                # "statut": publication.statut.value,
                # "url_publication": publication.url_publication,
                # "date_publication": publication.date_publication.isoformat() if publication.date_publication else None,
                # "date_programmee": publication.date_programmee.isoformat() if publication.date_programmee else None,
                # "contenu_publie": texte_contenu,
                # "image_utilisee": image_url
            # }
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur DB: {str(e)}")
        return jsonify({"error": "Erreur de base de données"}), 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur inattendue: {str(e)}")
        return jsonify({"error": "Erreur inattendue"}), 500


def get_all_publications():
    """Récupère toutes les publications selon les permissions"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if current_user.type_compte == TypeCompteEnum.admin:
        publications = Publication.query.all()
    else:
        publications = Publication.query.filter_by(id_utilisateur=current_user_id).all()

    return jsonify([p.to_dict() for p in publications]), 200


def get_publication_by_id(publication_id):
    """Récupère une publication par son ID"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    return jsonify(publication.to_dict()), 200
   
def update_publication(publication_id):
    """Met à jour une publication"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    data = request.get_json()
    try:
        if "titre_publication" in data:
            publication.titre_publication = data["titre_publication"]
        if "statut" in data:
            try:
                publication.statut = StatutPublicationEnum(data["statut"])
            except ValueError:
                return jsonify({"error": "Statut invalide"}), 400
        if "date_programmee" in data:
            publication.date_programmee = datetime.fromisoformat(data["date_programmee"]) if data["date_programmee"] else None
        if "parametres_publication" in data:
            publication.parametres_publication = data["parametres_publication"]
        if "url_publication" in data:
            publication.url_publication = data["url_publication"]
        if "id_externe" in data:
            publication.id_externe = data["id_externe"]
        if "message_erreur" in data:
            publication.message_erreur = data["message_erreur"]

        publication.date_modification = datetime.utcnow()
        db.session.commit()

        return jsonify({"message": "Publication mise à jour avec succès"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500
    

def delete_publication(publication_id):
    """Supprime une publication locale et sur X si applicable"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    try:
        # Supprimer sur X si la publication a été publiée
        if publication.id_externe and publication.statut == StatutPublicationEnum.publie:
            # Récupérer le token X de l'utilisateur
            token = Token.query.filter_by(
                utilisateur_id=current_user_id, 
                provider='x'
            ).first()
            
            if token and token.is_valid():
                current_app.logger.info(f"Tentative suppression X - Tweet ID: {publication.id_externe}")
                success, message = delete_publication_from_x(
                    publication.id_externe, 
                    token.access_token
                )
                if not success:
                    current_app.logger.warning(f"Échec suppression sur X : {message}")
                    # Option: retourner l'erreur ou continuer quand même
                    # return jsonify({"error": f"Impossible de supprimer sur X: {message}"}), 500
                else:
                    current_app.logger.info(f"Publication supprimée sur X : {message}")
            else:
                current_app.logger.warning("Token X invalide ou expiré pour l'utilisateur")
        else:
            current_app.logger.info(f"Publication locale uniquement (id_externe: {publication.id_externe}, statut: {publication.statut})")

        # Supprimer de la base de données
        db.session.delete(publication)
        db.session.commit()

        return jsonify({"message": "Publication supprimée avec succès"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur de base de données: {str(e)}")
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500

    except Exception as e:
        current_app.logger.error(f"Erreur lors de la suppression complète: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Erreur lors de la suppression: {str(e)}"}), 500    


def get_publication_stats():
    """Récupère les statistiques simples des publications"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if current_user.type_compte == TypeCompteEnum.admin:
        base_query = Publication.query
    else:
        base_query = Publication.query.filter_by(id_utilisateur=current_user_id)


    total_publications = base_query.count()

    stats_par_statut = {}
    for statut in StatutPublicationEnum:
        count = base_query.filter_by(statut=statut).count()
        stats_par_statut[statut.value] = count

    debut_semaine = datetime.now() - timedelta(days=7)
    publications_semaine = base_query.filter(
        Publication.date_creation >= debut_semaine
    ).count()

    maintenant = datetime.now()
    publications_programmees = base_query.filter(
        Publication.statut == StatutPublicationEnum.programme,
        Publication.date_programmee >= maintenant
    ).count()


    dernieres_publications = base_query.order_by(
        Publication.date_creation.desc()
    ).limit(5).all()

   
    plateforme_populaire = db.session.query(
        Publication.plateforme,
        func.count(Publication.id).label('count')
    ).group_by(Publication.plateforme).order_by(
        func.count(Publication.id).desc()
    ).first()

    stats = {
        "total": total_publications,
        "par_statut": stats_par_statut,
        "cette_semaine": publications_semaine,
        "a_venir": publications_programmees,
        "dernieres_publications": [
            {
                "id": pub.id,
                "titre": pub.titre_publication,
                "statut": pub.statut.value,
                "plateforme": pub.plateforme,
                "date_creation": pub.date_creation.isoformat() if pub.date_creation else None
            } for pub in dernieres_publications
        ],
        "plateforme_populaire": plateforme_populaire[0] if plateforme_populaire else None
    }

    return jsonify(stats), 200