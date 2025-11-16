from flask import request, jsonify, current_app
from app.extensions import db
from app.models.publication import Publication, StatutPublicationEnum
from app.models.utilisateur import Utilisateur, TypeCompteEnum, Token
from app.models.contenu import Contenu
from app.utils.identity import  get_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import requests
from app.services.x_service import publish_to_x_api, delete_publication_from_x
from app.scheduler.scheduler import scheduler  


def create_publication():
    
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        current_app.logger.error(f" JWT identity invalide: {current_user_id}")
        return jsonify({"error": "Token invalide"}), 401
    
    current_user = Utilisateur.query.get(current_user_id)
    if not current_user:
        current_app.logger.error(f" Utilisateur {current_user_id} non trouvé")
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.get_json()
    if not data or "id_contenu" not in data:
        return jsonify({"error": "Champ 'id_contenu' manquant"}), 400

    try:
        contenu = Contenu.query.get(data["id_contenu"])
        if not contenu:
            return jsonify({"error": "Contenu introuvable"}), 404
        
        if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
            current_app.logger.error(
                f"ACCÈS REFUSÉ - User {current_user_id} tente d'utiliser contenu {contenu.id} "
                f"(propriétaire: {contenu.id_utilisateur})"
            )
            return jsonify({"error": "Non autorisé à utiliser ce contenu"}), 403
        
        texte_contenu = data.get("message") or contenu.texte or contenu.titre or ""
        
        image_data = data.get("image_url") or contenu.image_url
        
        if not texte_contenu:
            return jsonify({"error": "Aucun contenu texte disponible pour la publication"}), 400

        now_utc = datetime.utcnow()
        
        statut = StatutPublicationEnum.brouillon
        date_programmee = None
        publier_maintenant = True
        task_id = None

        if data.get("date_programmee"):
            try:
                date_str = data["date_programmee"]
                date_str = date_str.replace('Z', '+00:00')
                date_programmee_aware = datetime.fromisoformat(date_str)
                
                if date_programmee_aware.tzinfo is not None:
                    date_programmee = date_programmee_aware.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    date_programmee = date_programmee_aware
                
                if date_programmee > now_utc:
                    statut = StatutPublicationEnum.programme
                    publier_maintenant = False
                else:
                    statut = StatutPublicationEnum.publie
                    publier_maintenant = True
                    date_programmee = None
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Erreur format date: {str(e)}")
                return jsonify({"error": "Format de date invalide"}), 400
        else:
            statut = StatutPublicationEnum.publie

        if data.get("statut") == "brouillon":
            statut = StatutPublicationEnum.brouillon
            publier_maintenant = False

        tweet_id = None
        url_publication = None
        tweet_data = {}

        if publier_maintenant:
            token = Token.query.filter_by(utilisateur_id=current_user_id, provider='x').first()
            if not token or not token.is_valid():
                return jsonify({"error": "Token X expiré ou manquant"}), 401

            url_publication, tweet_id, result = publish_to_x_api(
                texte_contenu,  
                token.access_token, 
                image_data  
            )

            if not url_publication and "Erreur" in (result or ""):
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

        titre_par_defaut = data.get("titre_publication") or getattr(
            contenu, "titre", f"Publication X - {now_utc.strftime('%d/%m/%Y')}"
        )

        publication = Publication(
            id_utilisateur=current_user_id,
            id_contenu=data["id_contenu"],
            plateforme='x',
            titre_publication=titre_par_defaut,
            statut=statut,
            date_programmee=date_programmee,
            date_publication=now_utc if statut == StatutPublicationEnum.publie else None,
            url_publication=url_publication,
            id_externe=tweet_id,
            parametres_publication={
                "tweet_id": tweet_id,
                "api_response": tweet_data,
                "publication_immediate": publier_maintenant,
                "message": texte_contenu,
                "image_url": image_data,  
                "task_id": task_id    
            }
        )
        
        db.session.add(publication)
        db.session.flush()
        
        if statut == StatutPublicationEnum.programme and date_programmee:
            try:
                if scheduler is None:
                    raise ImportError("Scheduler non disponible")
                
                date_programmee_aware = date_programmee.replace(tzinfo=timezone.utc)
                delay_seconds = (date_programmee_aware - datetime.now(timezone.utc)).total_seconds()

                if delay_seconds > 0:
                    job_id = f'publication_{publication.id}'
                    scheduler.scheduler.add_job(
                        func=scheduler.execute_publication_programmee,
                        trigger='date',
                        run_date=date_programmee_aware,
                        args=[publication.id],
                        id=job_id
                    )
                    task_id = job_id
                    publication.parametres_publication['task_id'] = task_id
                    current_app.logger.info(f" Tâche programmée: {task_id} pour {date_programmee_aware}")
                else:
                    current_app.logger.warning(f"Date déjà passée, pas de programmation")
                    
            except ImportError as e:
                current_app.logger.warning(f" Scheduler non disponible: {str(e)}")
            except Exception as e:
                current_app.logger.error(f" Erreur programmation: {str(e)}", exc_info=True)

        if statut == StatutPublicationEnum.publie:
            if hasattr(contenu, 'est_publie'):
                contenu.est_publie = True
            if hasattr(contenu, 'date_publication'):
                contenu.date_publication = now_utc

        db.session.commit()

        try:
            if publication.statut == StatutPublicationEnum.publie and publication.id_externe:
                # Vérifier que scheduler existe
                if scheduler is not None and hasattr(scheduler, 'update_publication_metrics'):
                    scheduler.update_publication_metrics(publication.id)
                    if hasattr(scheduler, 'planifier_updates_metrics'):
                        scheduler.planifier_updates_metrics(publication.id)
                else:
                    current_app.logger.warning("Scheduler ou méthodes metrics non disponibles")
        except Exception as e:
            current_app.logger.warning(f" Erreur planification métriques: {str(e)}")

        current_app.logger.info(f"Publication créée avec succès (ID: {publication.id})")

        return jsonify({
            "message": "Publication créée avec succès" if publier_maintenant else "Publication programmée avec succès",
            "publication": publication.to_dict()
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur DB: {str(e)}")
        return jsonify({"error": "Erreur de base de données"}), 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur inattendue: {str(e)}", exc_info=True)
        return jsonify({"error": "Erreur inattendue", "details": str(e)}), 500


def update_publication(publication_id):
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        current_app.logger.error(f" JWT identity invalide: {current_user_id}")
        return jsonify({"error": "Token invalide"}), 401
    
    current_user = Utilisateur.query.get(current_user_id)
    if not current_user:
        current_app.logger.error(f" Utilisateur {current_user_id} non trouvé")
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        current_app.logger.error(f"Publication {publication_id} introuvable")
        return jsonify({"error": "Publication introuvable"}), 404

    current_app.logger.info(f"🔍 Vérification permissions:")
    current_app.logger.info(f"  - User ID: {current_user_id} (type: {type(current_user_id)})")
    current_app.logger.info(f"  - Type compte: {current_user.type_compte}")
    current_app.logger.info(f"  - Publication owner: {publication.id_utilisateur} (type: {type(publication.id_utilisateur)})")
    
    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        current_app.logger.error(
            f" ACCÈS REFUSÉ - User {current_user_id} ({current_user.type_compte}) "
            f"tente de modifier publication {publication_id} (propriétaire: {publication.id_utilisateur})"
        )
        return jsonify({
            "error": "Non autorisé à modifier cette publication",
            "details": "Vous ne pouvez modifier que vos propres publications"
        }), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Aucune donnée fournie"}), 400
    
    current_app.logger.info(f" Données de mise à jour: {list(data.keys())}")

    try:
        champs_modifies = []
        
        if "titre_publication" in data:
            publication.titre_publication = data["titre_publication"]
            champs_modifies.append("titre")
            
        if "statut" in data:
            try:
                nouveau_statut = StatutPublicationEnum(data["statut"])
                ancien_statut = publication.statut
                publication.statut = nouveau_statut
                champs_modifies.append(f"statut ({ancien_statut.value} → {nouveau_statut.value})")
            except ValueError:
                return jsonify({"error": f"Statut invalide: {data['statut']}"}), 400
                
        if "date_programmee" in data:
            if data["date_programmee"]:
                date_str = data["date_programmee"].replace('Z', '+00:00')
                date_prog = datetime.fromisoformat(date_str)
                if date_prog.tzinfo is None:
                    date_prog = date_prog.replace(tzinfo=timezone.utc)
                publication.date_programmee = date_prog
                champs_modifies.append("date_programmee")
            else:
                publication.date_programmee = None
                champs_modifies.append("date_programmee (supprimée)")
                
        if "parametres_publication" in data:
            if publication.parametres_publication:
                publication.parametres_publication.update(data["parametres_publication"])
            else:
                publication.parametres_publication = data["parametres_publication"]
            champs_modifies.append("parametres")
            
        if "url_publication" in data:
            publication.url_publication = data["url_publication"]
            champs_modifies.append("url")
            
        if "id_externe" in data:
            publication.id_externe = data["id_externe"]
            champs_modifies.append("id_externe")
            
        if "message_erreur" in data:
            publication.message_erreur = data["message_erreur"]
            champs_modifies.append("message_erreur")

        publication.date_modification = datetime.now(timezone.utc)
        
        db.session.commit()
        
        current_app.logger.info(
            f" Publication {publication_id} modifiée par user {current_user_id}. "
            f"Champs: {', '.join(champs_modifies)}"
        )

        return jsonify({
            "message": "Publication mise à jour avec succès",
            "publication": publication.to_dict(),
            "champs_modifies": champs_modifies
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur DB: {str(e)}")
        return jsonify({"error": "Erreur de base de données", "details": str(e)}), 500
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur inattendue: {str(e)}")
        return jsonify({"error": "Erreur inattendue", "details": str(e)}), 500


def get_all_publications():
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Token invalide"}), 401
    
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if current_user.type_compte == TypeCompteEnum.admin:
        publications = Publication.query.all()
    else:
        publications = Publication.query.filter_by(id_utilisateur=current_user_id).all()

    return jsonify([p.to_dict() for p in publications]), 200


def get_publication_by_id(publication_id):
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Token invalide"}), 401
    
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    return jsonify(publication.to_dict()), 200


def delete_publication(publication_id):
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Token invalide"}), 401
    
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    try:
        if publication.id_externe and publication.statut == StatutPublicationEnum.publie:
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
                else:
                    current_app.logger.info(f"Publication supprimée sur X : {message}")
            else:
                current_app.logger.warning("Token X invalide ou expiré")
        else:
            current_app.logger.info(f"Publication locale uniquement")

        db.session.delete(publication)
        db.session.commit()

        return jsonify({"message": "Publication supprimée avec succès"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur DB: {str(e)}")
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500

    except Exception as e:
        current_app.logger.error(f" Erreur suppression: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Erreur lors de la suppression: {str(e)}"}), 500


def get_publication_stats():
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Token invalide"}), 401
    
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

    debut_semaine = datetime.now(timezone.utc) - timedelta(days=7)
    publications_semaine = base_query.filter(
        Publication.date_creation >= debut_semaine
    ).count()

    maintenant = datetime.now(timezone.utc)
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


def annuler_publication_programmee(publication_id):
    """Annule une publication programmée"""
    current_user_id = get_identity()
    
    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Token invalide"}), 401
    
    current_user = Utilisateur.query.get(current_user_id)
    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        current_app.logger.error(f" ACCÈS REFUSÉ pour annulation")
        return jsonify({
            "error": "Non autorisé à annuler cette publication",
            "details": "Vous ne pouvez annuler que vos propres publications"
        }), 403

    if publication.statut != StatutPublicationEnum.programme:
        return jsonify({
            "error": "Cette publication n'est pas programmée",
            "statut_actuel": publication.statut.value
        }), 400

    try:
        task_id = None
        try:
            task_id = (publication.parametres_publication or {}).get('task_id') or f'publication_{publication.id}'
            
            if scheduler is not None and hasattr(scheduler, 'scheduler'):
                job = scheduler.scheduler.get_job(task_id)
                if job:
                    scheduler.scheduler.remove_job(task_id)
                    current_app.logger.info(f" Tâche supprimée: {task_id}")
                else:
                    current_app.logger.warning(f" Tâche {task_id} introuvable")
            else:
                current_app.logger.warning(f" Scheduler non disponible")
        except Exception as e:
            current_app.logger.warning(f" Impossible de supprimer tâche: {str(e)}")

        publication.statut = StatutPublicationEnum.supprime
        publication.date_programmee = None
        publication.date_modification = datetime.now(timezone.utc)
        publication.message_erreur = None

        db.session.commit()

        current_app.logger.info(f"Publication {publication_id} annulée")

        return jsonify({
            "message": "Publication programmée annulée avec succès",
            "publication": publication.to_dict()
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur DB: {str(e)}")
        return jsonify({"error": "Erreur de base de données", "details": str(e)}), 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f" Erreur annulation: {str(e)}")
        return jsonify({"error": "Erreur lors de l'annulation", "details": str(e)}), 500