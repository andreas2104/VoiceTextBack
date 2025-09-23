import requests
from datetime import datetime, timedelta
from app.models.plateforme import Plateforme, StatutConnexionEnum
from app.models.publication import Publication, StatutPublicationEnum
from app.extensions import db

class SocialMediaService:
    
    @staticmethod
    def publier_sur_facebook(plateforme: Plateforme, publication: Publication, contenu_text: str, image_url=None):
        """Publie sur Facebook"""
        if not plateforme.is_token_valid():
            return {"success": False, "error": "Token expiré"}
        
        if not plateforme.peut_publier_aujourd_hui():
            return {"success": False, "error": "Limite quotidienne atteinte"}
        
        config = plateforme.get_api_config()
        url = f"{config['base_url']}{config['endpoints']['page_posts']}"
        
        payload = {
            'message': contenu_text,
            'access_token': plateforme.access_token
        }
        
        if image_url:
            payload['link'] = image_url
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            result = response.json()
            
            # Mise à jour de la publication
            publication.statut = StatutPublicationEnum.publie
            publication.date_publication = datetime.utcnow()
            publication.id_externe = result.get('id')
            publication.url_publication = f"https://facebook.com/{result.get('id')}"
            
            # Mise à jour des statistiques de la plateforme
            plateforme.posts_publies_aujourd_hui += 1
            plateforme.derniere_publication = datetime.utcnow()
            
            db.session.commit()
            
            return {"success": True, "id_externe": result.get('id')}
            
        except Exception as e:
            publication.statut = StatutPublicationEnum.echec
            publication.message_erreur = str(e)
            db.session.commit()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def publier_sur_linkedin(plateforme: Plateforme, publication: Publication, contenu_text: str, image_url=None):
        """Publie sur LinkedIn"""
        if not plateforme.is_token_valid():
            return {"success": False, "error": "Token expiré"}
        
        config = plateforme.get_api_config()
        url = f"{config['base_url']}{config['endpoints']['ugcPosts']}"
        
        headers = {
            'Authorization': f'Bearer {plateforme.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        # Structure du post LinkedIn
        payload = {
            "author": f"urn:li:organization:{plateforme.id_compte_externe}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": contenu_text
                    },
                    "shareMediaCategory": "ARTICLE" if image_url else "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        if image_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "media": image_url
                }
            ]
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Mise à jour de la publication
            publication.statut = StatutPublicationEnum.publie
            publication.date_publication = datetime.utcnow()
            publication.id_externe = result.get('id')
            
            # Mise à jour des statistiques
            plateforme.posts_publies_aujourd_hui += 1
            plateforme.derniere_publication = datetime.utcnow()
            
            db.session.commit()
            
            return {"success": True, "id_externe": result.get('id')}
            
        except Exception as e:
            publication.statut = StatutPublicationEnum.echec
            publication.message_erreur = str(e)
            db.session.commit()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def verifier_statut_token(plateforme: Plateforme):
        """Vérifie et met à jour le statut du token"""
        config = plateforme.get_api_config()
        
        if plateforme.nom_plateforme.value == 'facebook':
            url = f"{config['base_url']}/me"
            params = {'access_token': plateforme.access_token}
        else:  # LinkedIn
            url = f"{config['base_url']}/people/~"
            headers = {'Authorization': f'Bearer {plateforme.access_token}'}
            params = {}
        
        try:
            if plateforme.nom_plateforme.value == 'facebook':
                response = requests.get(url, params=params)
            else:
                response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                plateforme.statut_connexion = StatutConnexionEnum.connecte
                plateforme.derniere_synchronisation = datetime.utcnow()
            else:
                plateforme.statut_connexion = StatutConnexionEnum.expire
            
            db.session.commit()
            return response.status_code == 200
            
        except Exception as e:
            plateforme.statut_connexion = StatutConnexionEnum.erreur
            db.session.commit()
            return False