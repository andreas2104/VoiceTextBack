from flask import request, jsonify
from app.extensions import db
from app.models.historique import Historique, TypeActionEnum
from app.models.utilisateur import Utilisateur, TypeCompteEnum
from app.utils.identity import  get_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc

def get_all_historiques():
    """Récupère l'historique selon les permissions"""
    current_user_id = get_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    # Admin voit tout, utilisateur normal voit seulement ses actions
    if current_user.type_compte == TypeCompteEnum.admin:
        historiques = Historique.query.order_by(desc(Historique.date_action)).all()
    else:
        historiques = Historique.query.filter_by(id_utilisateur=current_user_id).order_by(desc(Historique.date_action)).all()

    return jsonify([h.to_dict() for h in historiques]), 200

def get_historique_by_contenu(contenu_id):
    """Récupère l'historique d'un contenu spécifique"""
    current_user_id = get_identity()
    current_user = Utilisateur.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if current_user.type_compte == TypeCompteEnum.admin:
        historiques = Historique.query.filter_by(id_contenu=contenu_id).order_by(desc(Historique.date_action)).all()
    else:
        historiques = Historique.query.filter_by(
            id_contenu=contenu_id, 
            id_utilisateur=current_user_id
        ).order_by(desc(Historique.date_action)).all()

    return jsonify([h.to_dict() for h in historiques]), 200

def create_historique_entry(id_utilisateur, type_action, description, id_contenu=None, id_plateforme=None, 
                          donnees_avant=None, donnees_apres=None, ip_utilisateur=None, user_agent=None):
    """Fonction utilitaire pour créer une entrée d'historique"""
    try:
        historique = Historique(
            id_utilisateur=id_utilisateur,
            id_contenu=id_contenu,
            id_plateforme=id_plateforme,
            type_action=type_action,
            description=description,
            donnees_avant=donnees_avant,
            donnees_apres=donnees_apres,
            ip_utilisateur=ip_utilisateur,
            user_agent=user_agent
        )
        
        db.session.add(historique)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        return False
