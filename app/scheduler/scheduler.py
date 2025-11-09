from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from flask import current_app
from datetime import datetime, timezone
import logging

class PublicationScheduler:
    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialiser le scheduler avec l'application Flask"""
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config.get('SQLALCHEMY_DATABASE_URI'))
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone='UTC'  # Important: définir le timezone
        )
        
        # Ajouter le contexte Flask
        self.app = app
        
        # NE PAS démarrer ici, mais dans app.py
        app.logger.info("✅ Scheduler initialisé (non démarré)")
    
    def start(self):
        """Démarrer le scheduler"""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            if self.app:
                self.app.logger.info("✅ Scheduler démarré avec succès")
        else:
            if self.app:
                self.app.logger.warning("⚠️ Scheduler déjà démarré ou non initialisé")
    
    def shutdown(self):
        """Arrêter proprement le scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            if self.app:
                self.app.logger.info("🛑 Scheduler arrêté")
    
    def execute_publication_programmee(self, publication_id):
        """Exécuter une publication programmée"""
        # IMPORTANT: Utiliser le contexte Flask
        with self.app.app_context():
            from app.models.publication import Publication, StatutPublicationEnum
            from app.models.utilisateur import Token
            from app.extensions import db
            from app.services.x_service import publish_to_x_api
            
            try:
                publication = Publication.query.get(publication_id)
                if not publication:
                    current_app.logger.error(f"❌ Publication {publication_id} introuvable")
                    return
                
                if publication.statut != StatutPublicationEnum.programme:
                    current_app.logger.warning(f"⚠️ Publication {publication_id} n'est pas programmée")
                    return
                
                # Récupérer le token
                token = Token.query.filter_by(
                    utilisateur_id=publication.id_utilisateur,
                    provider='x'
                ).first()
                
                if not token or not token.is_valid():
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = "Token X expiré"
                    db.session.commit()
                    return
                
                # Publier
                params = publication.parametres_publication or {}
                message = params.get('message', '')
                image_url = params.get('image_url')
                
                url_publication, tweet_id, result = publish_to_x_api(
                    message,
                    token.access_token,
                    image_url
                )
                
                if url_publication and tweet_id:
                    publication.statut = StatutPublicationEnum.publie
                    publication.date_publication = datetime.now(timezone.utc).replace(tzinfo=None)
                    publication.url_publication = url_publication
                    publication.id_externe = tweet_id
                    publication.parametres_publication['tweet_id'] = tweet_id
                    publication.parametres_publication['api_response'] = result
                    current_app.logger.info(f"✅ Publication {publication_id} publiée avec succès")
                else:
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = result
                    current_app.logger.error(f"❌ Échec publication {publication_id}")
                
                db.session.commit()
                
            except Exception as e:
                current_app.logger.error(f"❌ Erreur exécution publication {publication_id}: {str(e)}", exc_info=True)
                try:
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = str(e)
                    db.session.commit()
                except:
                    db.session.rollback()
    
    def update_publication_metrics(self, publication_id):
        """Mettre à jour les métriques d'une publication"""
        with self.app.app_context():
            from app.models.publication import Publication
            from app.extensions import db
            import requests
            
            try:
                publication = Publication.query.get(publication_id)
                if not publication or not publication.id_externe:
                    return
                
                # Logique de mise à jour des métriques
                current_app.logger.info(f"📊 Mise à jour métriques publication {publication_id}")
                
            except Exception as e:
                current_app.logger.error(f"❌ Erreur mise à jour métriques: {str(e)}")
    
    def planifier_updates_metrics(self, publication_id):
        """Planifier les mises à jour périodiques des métriques"""
        try:
            job_id = f'metrics_{publication_id}'
            
            # Supprimer l'ancien job s'il existe
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Planifier une mise à jour toutes les heures pendant 24h
            self.scheduler.add_job(
                func=self.update_publication_metrics,
                trigger='interval',
                hours=1,
                args=[publication_id],
                id=job_id,
                max_instances=1
            )
            
            if self.app:
                self.app.logger.info(f"📊 Métriques planifiées pour publication {publication_id}")
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"❌ Erreur planification métriques: {str(e)}")

# Instance globale
scheduler = PublicationScheduler()