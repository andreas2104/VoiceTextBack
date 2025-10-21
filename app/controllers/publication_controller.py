from flask import request, jsonify
from app.extensions import db
from app.models.publication import Publication, StatutPublicationEnum
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.models.contenu import Contenu
from app.models.plateforme import PlateformeConfig # Ligne corrigée ici
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from datetime import datetime, timedelta


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

def create_publication():
    """Crée une nouvelle publication"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    data = request.get_json()
    required_fields = ["id_contenu", "id_plateforme", "titre_publication"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Champs manquants: {', '.join(missing_fields)}"}), 400

    try:

        contenu = Contenu.query.get(data["id_contenu"])
        plateforme = PlateformeConfig.query.get(data["id_plateforme"]) 

        if not contenu or not plateforme:
            return jsonify({"error": "Contenu ou plateforme introuvable"}), 404

        if contenu.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
            return jsonify({"error": "Non autorisé pour ce contenu"}), 403

        statut = StatutPublicationEnum.brouillon
        if "statut" in data:
            try:
                statut = StatutPublicationEnum(data["statut"])
            except ValueError:
                return jsonify({"error": "Statut de publication invalide"}), 400

        publication = Publication(
            id_utilisateur=current_user_id,
            id_contenu=data["id_contenu"],
            id_plateforme=data["id_plateforme"],
            titre_publication=data["titre_publication"],
            statut=statut,
            date_programmee=datetime.fromisoformat(data["date_programmee"]) if data.get("date_programmee") else None,
            parametres_publication=data.get("parametres_publication", {})
        )

        db.session.add(publication)
        db.session.commit()

        return jsonify({
            "message": "Publication créée avec succès",
            "publication": publication.to_dict()
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500

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
    """Supprime une publication"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    publication = Publication.query.get(publication_id)
    if not publication:
        return jsonify({"error": "Publication introuvable"}), 404

    # Vérifier les permissions
    if publication.id_utilisateur != current_user_id and current_user.type_compte != TypeCompteEnum.admin:
        return jsonify({"error": "Non autorisé"}), 403

    try:
        db.session.delete(publication)
        db.session.commit()
        return jsonify({"message": "Publication supprimée avec succès"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur de base de données: {str(e)}"}), 500


# statistique
def get_publication_stats():
    """Récupère les statistiques simples des publications"""
    current_user_id = get_jwt_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    # Base query selon les permissions
    if current_user.type_compte == TypeCompteEnum.admin:
        base_query = Publication.query
    else:
        base_query = Publication.query.filter_by(id_utilisateur=current_user_id)

    # Statistiques de base
    total_publications = base_query.count()
    
    # Publications par statut
    stats_par_statut = {}
    for statut in StatutPublicationEnum:
        count = base_query.filter_by(statut=statut).count()
        stats_par_statut[statut.value] = count

    # Publications cette semaine
    debut_semaine = datetime.now() - timedelta(days=7)
    publications_semaine = base_query.filter(
        Publication.date_creation >= debut_semaine
    ).count()

    # Publications programmées à venir
    publications_programmees = base_query.filter(
        Publication.statut == StatutPublicationEnum.programme,
        Publication.date_programmee >= datetime.now()
    ).count()

    # Dernières publications (5 plus récentes)
    dernieres_publications = base_query.order_by(
        Publication.date_creation.desc()
    ).limit(5).all()

    # Plateforme la plus utilisée
    plateforme_populaire = db.session.query(
        Publication.id_plateforme,
        func.count(Publication.id).label('count')
    ).group_by(Publication.id_plateforme).order_by(
        func.count(Publication.id).desc()
    ).first()

    # Statistiques résumées
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
                "date_creation": pub.date_creation.isoformat()
            } for pub in dernieres_publications
        ],
        "plateforme_populaire": plateforme_populaire[0] if plateforme_populaire else None
    }

    return jsonify(stats), 200