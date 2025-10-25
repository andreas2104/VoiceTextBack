from celery import shared_task
from flask import current_app
from app.extensions import db
from app.services.publication_service import executer_publications_programmees

@shared_task
def tache_publications_programmees():
    """Tâche Celery pour exécuter automatiquement les publications programmées"""
    with current_app.app_context():
        current_app.logger.info(" Exécution planifiée des publications programmées...")
        nb_publications = executer_publications_programmees()
        current_app.logger.info(f" {nb_publications} publications traitées")
        return nb_publications
