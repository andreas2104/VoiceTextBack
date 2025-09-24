# app/routes/plateforme_routes.py
from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.plateforme_controller import PlateformeController

plateforme_bp = Blueprint("plateforme_bp", __name__, url_prefix="/plateformes")

# Routes de base
@plateforme_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_all_plateformes():
    """Récupère toutes les plateformes de l'utilisateur"""
    return PlateformeController.lister_plateformes()

@plateforme_bp.route("/<int:plateforme_id>", methods=["GET"])
@jwt_required()
def get_plateforme_by_id(plateforme_id):
    """Récupère une plateforme par son ID"""
    return PlateformeController.obtenir_plateforme(plateforme_id)

@plateforme_bp.route("/<int:plateforme_id>", methods=["DELETE"])
@jwt_required()
def delete_plateforme(plateforme_id):
    """Supprime une plateforme"""
    return PlateformeController.deconnecter_plateforme(plateforme_id)

# Routes de connexion et gestion
@plateforme_bp.route("/connecter", methods=["POST"])
@jwt_required()
def connecter_plateforme():
    """Connecte une nouvelle plateforme (Facebook/LinkedIn)"""
    return PlateformeController.connecter_plateforme()

@plateforme_bp.route("/status", methods=["GET"])
@jwt_required()
def verifier_statut_connexion():
    """Vérifie le statut de connexion de toutes les plateformes"""
    return PlateformeController.verifier_statut_connexion()

# Routes de publication
@plateforme_bp.route("/<int:plateforme_id>/publier", methods=["POST"])
@jwt_required()
def publier_contenu(plateforme_id):
    """Publie un contenu sur une plateforme spécifique"""
    return PlateformeController.publier_sur_plateforme(plateforme_id)

# Routes de statistiques et monitoring
@plateforme_bp.route("/<int:plateforme_id>/statistiques", methods=["GET"])
@jwt_required()
def get_statistiques_plateforme(plateforme_id):
    """Récupère les statistiques d'une plateforme"""
    return PlateformeController.obtenir_statistiques(plateforme_id)

@plateforme_bp.route("/<int:plateforme_id>/verifier-token", methods=["POST"])
@jwt_required()
def verifier_token_plateforme(plateforme_id):
    """Vérifie la validité du token d'une plateforme"""
    return PlateformeController.rafraichir_token(plateforme_id)

@plateforme_bp.route("/<int:plateforme_id>/deconnecter", methods=["POST"])
@jwt_required()
def deconnecter_plateforme(plateforme_id):
    """Déconnecte une plateforme"""
    return PlateformeController.deconnecter_plateforme(plateforme_id)

# Routes supplémentaires utiles
@plateforme_bp.route("/actives", methods=["GET"])
@jwt_required()
def lister_plateformes_actives():
    """Liste uniquement les plateformes actives"""
    from flask_jwt_extended import get_jwt_identity
    from flask import jsonify
    
    try:
        current_user_id = get_jwt_identity()
        from app.models.plateforme import Plateforme
        
        plateformes_actives = Plateforme.get_active_platforms(current_user_id)
        
        return jsonify({
            "success": True,
            "data": [p.to_dict() for p in plateformes_actives],
            "count": len(plateformes_actives)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@plateforme_bp.route("/<int:plateforme_id>/parametres", methods=["PUT"])
@jwt_required()
def update_parametres_plateforme(plateforme_id):
    """Met à jour les paramètres d'une plateforme"""
    from flask import request, jsonify
    from flask_jwt_extended import get_jwt_identity
    
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        from app.models.plateforme import Plateforme
        from app.extensions import db
        
        plateforme = Plateforme.query.get(plateforme_id)
        if not plateforme:
            return jsonify({"error": "Plateforme non trouvée"}), 404
        
        if plateforme.id_utilisateur != current_user_id:
            return jsonify({"error": "Accès non autorisé"}), 403
        
        # Mettre à jour les paramètres autorisés
        updatable_fields = ['limite_posts_jour', 'nom_compte', 'actif']
        updated = False
        
        for field in updatable_fields:
            if field in data:
                setattr(plateforme, field, data[field])
                updated = True
        
        if updated:
            plateforme.date_modification = db.func.now()
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Paramètres mis à jour avec succès",
                "data": plateforme.to_dict()
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Aucun paramètre valide à mettre à jour"
            }), 400
            
    except Exception as e:
        from app.extensions import db
        db.session.rollback()
        return jsonify({"error": str(e)}), 500