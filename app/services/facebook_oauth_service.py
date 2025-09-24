import requests
import urllib.parse
from flask import current_app, url_for
from app.models.plateforme import TypePlateformeEnum

class FacebookOAuthService:
    
    @staticmethod
    def get_authorization_url():
        """Génère l'URL d'autorisation Facebook"""
        base_url = "https://www.facebook.com/v18.0/dialog/oauth"
        
        params = {
            'client_id': current_app.config['FACEBOOK_APP_ID'],
            'redirect_uri': current_app.config['FACEBOOK_REDIRECT_URI'],
            'scope': 'pages_manage_posts,pages_read_engagement,pages_show_list',
            'response_type': 'code',
            'state': 'facebook_auth'  # Pour la sécurité CSRF
        }
        
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_token(code):
        """Échange le code d'autorisation contre un access token"""
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            'client_id': current_app.config['FACEBOOK_APP_ID'],
            'client_secret': current_app.config['FACEBOOK_APP_SECRET'],
            'redirect_uri': current_app.config['FACEBOOK_REDIRECT_URI'],
            'code': code
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' in data:
                return {
                    'success': True,
                    'access_token': data['access_token'],
                    'expires_in': data.get('expires_in', 3600)
                }
            else:
                return {
                    'success': False,
                    'error': data.get('error', {}).get('message', 'Token exchange failed')
                }
                
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    
    @staticmethod
    def get_long_lived_token(short_token):
        """Convertit un token de courte durée en token longue durée"""
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': current_app.config['FACEBOOK_APP_ID'],
            'client_secret': current_app.config['FACEBOOK_APP_SECRET'],
            'fb_exchange_token': short_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'access_token': data['access_token'],
                'expires_in': data.get('expires_in', 5183944)  # ~60 jours
            }
            
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Long-lived token exchange failed: {str(e)}'
            }
    
    @staticmethod
    def get_user_pages(access_token):
        """Récupère les pages Facebook de l'utilisateur"""
        url = "https://graph.facebook.com/v18.0/me/accounts"
        
        params = {
            'access_token': access_token,
            'fields': 'id,name,access_token,category,tasks'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            pages = []
            for page in data.get('data', []):
                # Vérifier si on peut publier sur cette page
                tasks = page.get('tasks', [])
                can_post = 'MANAGE' in tasks or 'CREATE_CONTENT' in tasks
                
                if can_post:
                    pages.append({
                        'id': page['id'],
                        'name': page['name'],
                        'category': page['category'],
                        'access_token': page['access_token'],
                        'can_post': True
                    })
            
            return {
                'success': True,
                'pages': pages
            }
            
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Failed to fetch pages: {str(e)}'
            }
    
    @staticmethod
    def verify_token(access_token):
        """Vérifie la validité d'un token Facebook"""
        url = "https://graph.facebook.com/v18.0/me"
        
        params = {
            'access_token': access_token,
            'fields': 'id,name'
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return {
                    'success': True,
                    'valid': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': True,
                    'valid': False,
                    'error': 'Token expired or invalid'
                }
                
        except requests.RequestException:
            return {
                'success': False,
                'valid': False,
                'error': 'Token verification failed'
            }