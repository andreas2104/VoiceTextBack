from flask import current_app
from app.extensions import db
from app.models.publication import Publication, StatutPublicationEnum
from app.models.utilisateur import Token
from app.models.contenu import Contenu
from app.services.x_service import publish_to_x_api
from datetime import datetime

def executer_publications_programmees():
    """Exécute les publications programmées dont la date est passée"""
    try:
        publications = Publication.query.filter(
            Publication.statut == StatutPublicationEnum.programme,
            Publication.date_programmee <= datetime.utcnow()
        ).all()

        current_app.logger.info(f"Exécution de {len(publications)} publications programmées")

        for publication in publications:
            try:
                # Récupérer le token et le contenu
                token = Token.query.filter_by(
                    utilisateur_id=publication.id_utilisateur,
                    provider=publication.plateforme
                ).first()
                
                contenu = Contenu.query.get(publication.id_contenu)
                
                if not token or not token.is_valid():
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = "Token invalide ou expiré"
                    continue
                
                if not contenu:
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = "Contenu introuvable"
                    continue

                # Publier sur X
                url_publication, tweet_id, tweet_data = publish_to_x_api(
                    contenu.contenu, 
                    token.access_token
                )
                
                if url_publication and tweet_id:
                    # Succès
                    publication.statut = StatutPublicationEnum.publie
                    publication.date_publication = datetime.utcnow()
                    publication.url_publication = url_publication
                    publication.id_externe = tweet_id
                    
                    # Mettre à jour le contenu
                    contenu.est_publie = True
                    contenu.date_publication = datetime.utcnow()
                    
                    current_app.logger.info(f"Publication {publication.id} publiée avec succès, tweet ID: {tweet_id}")
                else:
                    # Échec
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = tweet_data  # Contient le message d'erreur
                    current_app.logger.error(f"Échec publication {publication.id}: {tweet_data}")

            except Exception as e:
                current_app.logger.error(f"Erreur publication {publication.id}: {str(e)}")
                publication.statut = StatutPublicationEnum.echec
                publication.message_erreur = f"Erreur inattendue: {str(e)}"
                continue

        db.session.commit()
        return len(publications)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur générale dans executer_publications_programmees: {str(e)}")
        return 0