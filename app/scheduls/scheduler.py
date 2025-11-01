from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone
from flask import current_app
from app.extensions import db
from app.models.publication import Publication, StatutPublicationEnum
from app.models.utilisateur import Token
from app.models.contenu import Contenu
from app.services.x_service import publish_to_x_api, get_tweet_metrics
import logging

# Configuration du logger
logger = logging.getLogger(__name__)

class PublicationScheduler:
    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler()
        self.app = app
        
    def init_app(self, app):
        self.app = app
        self.setup_scheduler()
        
    def setup_scheduler(self):
        """Configure les tâches planifiées"""
        try:
            # Vérifier les publications en retard toutes les 5 minutes
            self.scheduler.add_job(
                id='verifier_publications_en_retard',
                func=self.verifier_publications_en_retard,
                trigger=IntervalTrigger(minutes=5),
                replace_existing=True
            )
            
            # Mettre à jour les métriques toutes les heures
            self.scheduler.add_job(
                id='update_all_publications_metrics',
                func=self.update_all_publications_metrics,
                trigger=IntervalTrigger(hours=1),
                replace_existing=True
            )
            
            # Nettoyer les anciennes tâches tous les jours à 2h
            self.scheduler.add_job(
                id='nettoyer_anciennes_taches',
                func=self.nettoyer_anciennes_taches,
                trigger=CronTrigger(hour=2, minute=0),
                replace_existing=True
            )
            
            logger.info("✅ Scheduler APScheduler configuré avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur configuration scheduler: {str(e)}")
    
    def start(self):
        """Démarre le scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 Scheduler APScheduler démarré")
    
    def shutdown(self):
        """Arrête le scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler APScheduler arrêté")

    # ---- Metrics helpers ----
    def update_publication_metrics(self, publication_id: int) -> bool:
        try:
            with self.app.app_context():
                pub = Publication.query.get(publication_id)
                if not pub or not pub.id_externe:
                    return False

                token = Token.query.filter_by(
                    utilisateur_id=pub.id_utilisateur,
                    provider='x'
                ).first()
                if not token or not token.is_valid():
                    return False

                metrics = get_tweet_metrics(pub.id_externe, token.access_token)
                if not metrics:
                    return False

                pub.nombre_vues = metrics.get('views', 0)
                pub.nombre_likes = metrics.get('likes', 0)
                pub.nombre_partages = metrics.get('retweets', 0) + metrics.get('quotes', 0)
                pub.date_modification = datetime.now(timezone.utc)
                db.session.commit()
                logger.info(f"📊 Metrics mis à jour pour pub {publication_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour métriques pub {publication_id}: {str(e)}")
            return False

    def planifier_updates_metrics(self, publication_id: int):
        try:
            # Planifie quelques mises à jour initiales après publication pour capter l'engagement
            now = datetime.now(timezone.utc)
            schedules = [5, 30, 120]  # minutes après publication
            for minutes_after in schedules:
                run_time = now + timedelta(minutes=minutes_after)
                job_id = f'metrics_{publication_id}_{minutes_after}m'
                self.scheduler.add_job(
                    id=job_id,
                    func=self.update_publication_metrics,
                    trigger='date',
                    run_date=run_time,
                    args=[publication_id],
                    replace_existing=True
                )
            logger.info(f"🗓️ Metrics jobs planifiés pour pub {publication_id}")
        except Exception as e:
            logger.error(f"❌ Erreur planification metrics pub {publication_id}: {str(e)}")

    # Tâches du scheduler
    def execute_publication_programmee(self, publication_id, max_retries=3, current_retry=0):
        """
        Exécute une publication programmée (remplace la tâche Celery)
        
        Args:
            publication_id (int): ID de la publication
            max_retries (int): Nombre maximum de tentatives
            current_retry (int): Tentative actuelle
        """
        try:
            with self.app.app_context():
                publication = Publication.query.get(publication_id)
                if not publication:
                    logger.error(f"❌ Publication {publication_id} introuvable")
                    return False

                if publication.statut != StatutPublicationEnum.programme:
                    logger.warning(
                        f"⚠️ Publication {publication_id} n'est pas en statut 'programmé' (statut: {publication.statut})"
                    )
                    return False

                # Récupérer le token
                token = Token.query.filter_by(
                    utilisateur_id=publication.id_utilisateur, 
                    provider='x'
                ).first()

                if not token or not token.is_valid():
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = "Token X expiré ou manquant"
                    publication.date_modification = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.error(f"❌ Token invalide pour publication {publication_id}")
                    return False

                # Récupérer le contenu
                contenu = Contenu.query.get(publication.id_contenu)
                if not contenu:
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = "Contenu introuvable"
                    publication.date_modification = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.error(f"❌ Contenu introuvable pour publication {publication_id}")
                    return False

                # Préparer les données
                parametres = publication.parametres_publication or {}
                texte_contenu = parametres.get("message", "") or contenu.texte or contenu.titre or ""
                image_url = parametres.get("image_url") or contenu.image_url

                if not texte_contenu:
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = "Aucun contenu texte disponible"
                    publication.date_modification = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.error(f"❌ Pas de texte pour publication {publication_id}")
                    return False

                # Publication sur X
                logger.info(f"📤 Publication {publication_id} en cours...")
                url_publication, tweet_id, result = publish_to_x_api(
                    texte_contenu, 
                    token.access_token, 
                    image_url
                )

                # Mise à jour du statut
                now = datetime.now(timezone.utc)
                
                if url_publication and tweet_id:
                    publication.statut = StatutPublicationEnum.publie
                    publication.date_publication = now
                    publication.url_publication = url_publication
                    publication.id_externe = tweet_id
                    publication.message_erreur = None
                    publication.parametres_publication = {
                        **parametres,
                        "tweet_id": tweet_id,
                        "api_response": result,
                        "date_execution_reelle": now.isoformat(),
                        "executed_by": "apscheduler"
                    }

                    # Marquer le contenu comme publié
                    if hasattr(contenu, 'est_publie'):
                        contenu.est_publie = True
                    if hasattr(contenu, 'date_publication'):
                        contenu.date_publication = now

                    logger.info(f"✅ Publication programmée exécutée: {publication_id} → {url_publication}")
                    # Planifier des récupérations de métriques initiales
                    try:
                        self.planifier_updates_metrics(publication_id)
                    except Exception:
                        pass
                else:
                    publication.statut = StatutPublicationEnum.echec
                    publication.message_erreur = result or "Erreur inconnue"
                    logger.error(f"❌ Échec publication: {publication_id} - {result}")

                publication.date_modification = now
                db.session.commit()
                
                return publication.statut == StatutPublicationEnum.publie

        except Exception as e:
            logger.error(f"❌ Erreur exécution publication {publication_id}: {str(e)}")
            
            # Retry logic
            if current_retry < max_retries:
                logger.info(f"🔄 Retry {current_retry + 1}/{max_retries} dans 5 minutes...")
                self.scheduler.add_job(
                    func=self.execute_publication_programmee,
                    trigger=IntervalTrigger(minutes=5),
                    args=[publication_id, max_retries, current_retry + 1],
                    id=f'retry_publication_{publication_id}_{current_retry + 1}'
                )
            else:
                # Échec final
                try:
                    publication = Publication.query.get(publication_id)
                    if publication:
                        publication.statut = StatutPublicationEnum.echec
                        publication.message_erreur = f"Échec après {max_retries} tentatives: {str(e)}"
                        publication.date_modification = datetime.now(timezone.utc)
                        db.session.commit()
                except:
                    pass
            
            return False

    def verifier_publications_en_retard(self):
        """
        Vérifie les publications en retard (exécuté toutes les 5 minutes)
        """
        try:
            with self.app.app_context():
                now = datetime.now(timezone.utc)
                
                publications_en_retard = Publication.query.filter(
                    Publication.statut == StatutPublicationEnum.programme,
                    Publication.date_programmee < now
                ).all()

                if not publications_en_retard:
                    logger.info("✅ Aucune publication en retard")
                    return

                logger.info(f"🚀 {len(publications_en_retard)} publication(s) en retard détectée(s)")

                for publication in publications_en_retard:
                    logger.info(f"📤 Exécution de publication en retard: {publication.id}")
                    # Exécuter immédiatement
                    self.execute_publication_programmee(publication.id)
                    
        except Exception as e:
            logger.error(f"❌ Erreur vérification publications en retard: {str(e)}")

    def update_all_publications_metrics(self):
        """
        Met à jour les métriques des publications (exécuté toutes les heures)
        """
        try:
            with self.app.app_context():
                date_limite = datetime.now(timezone.utc) - timedelta(days=7)
                
                publications = Publication.query.filter(
                    Publication.statut == StatutPublicationEnum.publie,
                    Publication.date_publication >= date_limite,
                    Publication.id_externe.isnot(None)
                ).all()
                
                if not publications:
                    logger.info("✅ Aucune publication récente à mettre à jour")
                    return
                
                logger.info(f"📊 Mise à jour des métriques pour {len(publications)} publication(s)")
                
                updated_count = 0
                
                for pub in publications:
                    try:
                        token = Token.query.filter_by(
                            utilisateur_id=pub.id_utilisateur, 
                            provider='x'
                        ).first()
                        
                        if not token or not token.is_valid():
                            continue
                        
                        metrics = get_tweet_metrics(pub.id_externe, token.access_token)
                        
                        if metrics:
                            pub.nombre_vues = metrics.get('views', 0)
                            pub.nombre_likes = metrics.get('likes', 0)
                            pub.nombre_partages = metrics.get('retweets', 0) + metrics.get('quotes', 0)
                            pub.date_modification = datetime.now(timezone.utc)
                            updated_count += 1
                            
                            logger.debug(
                                f"📈 Pub {pub.id}: {pub.nombre_likes} likes, "
                                f"{pub.nombre_vues} vues, {pub.nombre_partages} partages"
                            )
                    
                    except Exception as e:
                        logger.error(f"❌ Erreur métrique pub {pub.id}: {str(e)}")
                        continue
                
                db.session.commit()
                logger.info(f"✅ {updated_count} publication(s) mise(s) à jour")
                
        except Exception as e:
            logger.error(f"❌ Erreur critique mise à jour métriques: {str(e)}")

    def nettoyer_anciennes_taches(self):
        """
        Nettoie les anciennes publications (exécuté tous les jours à 2h)
        """
        try:
            with self.app.app_context():
                date_limite = datetime.now(timezone.utc) - timedelta(days=30)
                
                anciennes_publications = Publication.query.filter(
                    Publication.statut == StatutPublicationEnum.echec,
                    Publication.date_creation < date_limite
                ).all()
                
                if not anciennes_publications:
                    logger.info("✅ Aucune publication à nettoyer")
                    return
                
                count = len(anciennes_publications)
                
                for pub in anciennes_publications:
                    db.session.delete(pub)
                
                db.session.commit()
                
                logger.info(f"🧹 {count} publication(s) en échec supprimée(s)")
                
        except Exception as e:
            logger.error(f"❌ Erreur nettoyage: {str(e)}")

# Instance globale du scheduler
scheduler = PublicationScheduler()