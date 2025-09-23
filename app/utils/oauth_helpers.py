import requests
from urllib.parse import urlencode
import os

class FacebookOAuthHelper:
    
    @staticmethod
    def get_auth_url(redirect_uri, state):
        """Génère l'URL d'autorisation Facebook"""
        base_url = "https://www.facebook.com/v18.0/dialog/oauth"
        params = {
            'client_id': os.getenv('FACEBOOK_APP_ID'),
            'redirect_uri': redirect_uri,
            'scope': 'pages_manage_posts,pages_read_engagement,pages_show_list',
            'response_type': 'code',
            'state': state
        }
        return f"{base_url}?{urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_token(code, redirect_uri):
        """Échange le code d'autorisation contre un access token"""
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            'client_id': os.getenv('FACEBOOK_APP_ID'),
            'client_secret': os.getenv('FACEBOOK_APP_SECRET'),
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return None
    
    @staticmethod
    def get_user_pages(access_token):
        """Récupère les pages gérées par l'utilisateur"""
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            'access_token': access_token,
            'fields': 'name,id,access_token,category'
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('data', [])
        return []

class LinkedInOAuthHelper:
    
    @staticmethod
    def get_auth_url(redirect_uri, state):
        """Génère l'URL d'autorisation LinkedIn"""
        base_url = "https://www.linkedin.com/oauth/v2/authorization"
        params = {
            'response_type': 'code',
            'client_id': os.getenv('LINKEDIN_CLIENT_ID'),
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': 'w_member_social,r_organization_social,w_organization_social'
        }
        return f"{base_url}?{urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_token(code, redirect_uri):
        """Échange le code d'autorisation contre un access token"""
        url = "https://www.linkedin.com/oauth/v2/accessToken"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': os.getenv('LINKEDIN_CLIENT_ID'),
            'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET'),
            'redirect_uri': redirect_uri
        }
        
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        return None
    
    @staticmethod
    def get_user_organizations(access_token):
        """Récupère les organisations gérées par l'utilisateur"""
        url = "https://api.linkedin.com/v2/organizationalEntityAcls"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        params = {
            'q': 'roleAssignee',
            'role': 'ADMINISTRATOR'
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get('elements', [])
        return []