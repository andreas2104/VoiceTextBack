from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime, timedelta

from app.extensions import db
from app.models.plateforme import Plateforme, TypePlateformeEnum, StatutConnexionEnum
from app.models.utilisateur import Utilisateur
from app.services.social_media_service import SocialMediaService  # Import du service

class PlateformeController:
    
    @staticmethod
    @jwt_required()
    def connecter_plateforme():
        """Connecte une nouvelle plateforme (Facebook ou LinkedIn)"""
        try:
            current_user_id = get_jwt_identity()
            data = request.get_json()
            
            # Validation des données
            if not data:
                return jsonify({"error": "Données JSON manquantes"}), 400
            
            required_fields = ["nom_plateforme", "access_token", "nom_compte"]
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return jsonify({
                    "error": f"Champs manquants: {', '.join(missing_fields)}"
                }), 400
            
            # Validation du type de plateforme
            try:
                platform_type = TypePlateformeEnum(data["nom_plateforme"])
            except ValueError:
                return jsonify({
                    "error": f"Plateforme non supportée. Plateformes disponibles: {[e.value for e in TypePlatformeEnum]}"
                }), 400
            
            # Vérifier si l'utilisateur existe
            user = Utilisateur.query.get(current_user_id)
            if not user:
                return jsonify({"error": "Utilisateur non trouvé"}), 404
            
            # Vérifier si la plateforme existe déjà pour cet utilisateur
            existing_platform = Plateforme.get_by_user_and_platform(current_user_id, platform_type)
            
            if existing_platform:
                # Mettre à jour la plateforme existante
                existing_platform.access_token = data["access_token"]
                existing_platform.refresh_token = data.get("refresh_token")
                existing_platform.nom_compte = data["nom_compte"]
                existing_platform.id_compte_externe = data.get("id_compte_externe")
                existing_platform.token_expiration = datetime.utcnow() + timedelta(days=60)
                existing_platform.statut_connexion = StatutConnexionEnum.CONNECTE
                existing_platform.permissions_accordees = data.get("permissions", [])
                existing_platform.actif = True
                existing_platform.date_modification = datetime.utcnow()
                
                plateforme = existing_platform
                message = "Plateforme mise à jour avec succès"
            else:
                # Créer une nouvelle plateforme
                plateforme = Plateforme(
                    id_utilisateur=current_user_id,
                    nom_plateforme=platform_type,
                    nom_compte=data["nom_compte"],
                    id_compte_externe=data.get("id_compte_externe"),
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    token_expiration=datetime.utcnow() + timedelta(days=60),
                    statut_connexion=StatutConnexionEnum.CONNECTE,
                    permissions_accordees=data.get("permissions", []),
                    limite_posts_jour=data.get("limite_posts_jour", 25)
                )
                db.session.add(plateforme)
                message = "Plateforme connectée avec succès"
            
            db.session.commit()
            
            # Vérifier le statut du token après la connexion
            SocialMediaService.verifier_statut_token(plateforme)
            
            return jsonify({
                "success": True,
                "message": message,
                "data": plateforme.to_dict()
            }), 201
            
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Cette plateforme est déjà connectée"}), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({"error": "Erreur de base de données"}), 500
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def lister_plateformes():
        """Liste toutes les plateformes de l'utilisateur connecté"""
        try:
            current_user_id = get_jwt_identity()
            
            plateformes = Plateforme.query.filter_by(id_utilisateur=current_user_id).all()
            
            return jsonify({
                "success": True,
                "data": [p.to_dict() for p in plateformes],
                "count": len(plateformes)
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def obtenir_plateforme(plateforme_id):
        """Obtient les détails d'une plateforme spécifique"""
        try:
            current_user_id = get_jwt_identity()
            
            plateforme = Plateforme.query.get(plateforme_id)
            if not plateforme:
                return jsonify({"error": "Plateforme non trouvée"}), 404
            
            # Vérifier que la plateforme appartient à l'utilisateur
            if plateforme.id_utilisateur != current_user_id:
                return jsonify({"error": "Accès non autorisé"}), 403
            
            return jsonify({
                "success": True,
                "data": plateforme.to_dict()
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def deconnecter_plateforme(plateforme_id):
        """Déconnecte une plateforme"""
        try:
            current_user_id = get_jwt_identity()
            
            plateforme = Plateforme.query.get(plateforme_id)
            if not plateforme:
                return jsonify({"error": "Plateforme non trouvée"}), 404
            
            # Vérifier que la plateforme appartient à l'utilisateur
            if plateforme.id_utilisateur != current_user_id:
                return jsonify({"error": "Accès non autorisé"}), 403
            
            # Mettre à jour le statut de connexion
            plateforme.statut_connexion = StatutConnexionEnum.DECONNECTE
            plateforme.actif = False
            plateforme.access_token = None
            plateforme.refresh_token = None
            plateforme.token_expiration = None
            plateforme.date_modification = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Plateforme déconnectée avec succès",
                "data": plateforme.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def obtenir_statistiques(plateforme_id):
        """Obtient les statistiques d'une plateforme"""
        try:
            current_user_id = get_jwt_identity()
            
            plateforme = Plateforme.query.get(plateforme_id)
            if not plateforme:
                return jsonify({"error": "Plateforme non trouvée"}), 404
            
            # Vérifier que la plateforme appartient à l'utilisateur
            if plateforme.id_utilisateur != current_user_id:
                return jsonify({"error": "Accès non autorisé"}), 403
            
            # Calculer les statistiques
            stats = {
                "plateforme_info": plateforme.to_dict(),
                "peut_publier": plateforme.peut_publier_aujourd_hui(),
                "token_valide": plateforme.is_token_valid(),
                "posts_restants_aujourd_hui": plateforme.limite_posts_jour - plateforme.posts_publies_aujourd_hui,
                "pourcentage_utilisation": round((plateforme.posts_publies_aujourd_hui / plateforme.limite_posts_jour) * 100, 2) if plateforme.limite_posts_jour > 0 else 0
            }
            
            return jsonify({
                "success": True,
                "data": stats
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def verifier_statut_connexion():
        """Vérifie le statut de connexion de toutes les plateformes de l'utilisateur"""
        try:
            current_user_id = get_jwt_identity()
            
            plateformes = Plateforme.get_active_platforms(current_user_id)
            
            statuts = []
            for plateforme in plateformes:
                # Vérifier le statut actuel du token via le service
                SocialMediaService.verifier_statut_token(plateforme)
                
                statut = {
                    "id": plateforme.id,
                    "nom_plateforme": plateforme.nom_plateforme.value,
                    "nom_compte": plateforme.nom_compte,
                    "statut_connexion": plateforme.statut_connexion.value,
                    "token_valide": plateforme.is_token_valid(),
                    "peut_publier": plateforme.peut_publier_aujourd_hui()
                }
                statuts.append(statut)
            
            return jsonify({
                "success": True,
                "data": statuts
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def publier_sur_plateforme(plateforme_id):
        """Publie du contenu sur une plateforme spécifique"""
        try:
            current_user_id = get_jwt_identity()
            data = request.get_json()
            
            # Validation des données
            if not data or not data.get('contenu'):
                return jsonify({"error": "Contenu de publication manquant"}), 400
            
            # Récupérer la plateforme
            plateforme = Plateforme.query.get(plateforme_id)
            if not plateforme:
                return jsonify({"error": "Plateforme non trouvée"}), 404
            
            # Vérifier les permissions
            if plateforme.id_utilisateur != current_user_id:
                return jsonify({"error": "Accès non autorisé"}), 403
            
            if not plateforme.is_token_valid():
                return jsonify({"error": "Token de plateforme expiré"}), 400
            
            if not plateforme.peut_publier_aujourd_hui():
                return jsonify({"error": "Limite de publications quotidienne atteinte"}), 400
            
            # Utiliser le service pour publier
            contenu = data['contenu']
            image_url = data.get('image_url')
            
            if plateforme.nom_plateforme == TypePlateformeEnum.FACEBOOK:
                result = SocialMediaService.publier_sur_facebook(
                    plateforme, contenu, image_url
                )
            elif plateforme.nom_plateforme == TypePlateformeEnum.LINKEDIN:
                result = SocialMediaService.publier_sur_linkedin(
                    plateforme, contenu, image_url
                )
            else:
                return jsonify({"error": "Plateforme non supportée"}), 400
            
            if result['success']:
                return jsonify({
                    "success": True,
                    "message": "Publication réussie",
                    "data": result
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": result['error']
                }), 400
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @jwt_required()
    def rafraichir_token(plateforme_id):
        """Tente de rafraîchir le token d'une plateforme"""
        try:
            current_user_id = get_jwt_identity()
            
            plateforme = Plateforme.query.get(plateforme_id)
            if not plateforme:
                return jsonify({"error": "Plateforme non trouvée"}), 404
            
            if plateforme.id_utilisateur != current_user_id:
                return jsonify({"error": "Accès non autorisé"}), 403
            
            # Vérifier le statut actuel
            token_valide = SocialMediaService.verifier_statut_token(plateforme)
            
            return jsonify({
                "success": True,
                "token_valide": token_valide,
                "statut_connexion": plateforme.statut_connexion.value,
                "message": "Statut du token vérifié avec succès"
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500