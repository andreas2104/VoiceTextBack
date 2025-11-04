import requests
from flask import current_app

def publish_to_x_api(texte_contenu, access_token, image_url=None):
    """
    Publie sur X (Twitter) avec le texte et l'image fournis
    
    Args:
        texte_contenu (str): Le texte à publier
        access_token (str): Token d'accès OAuth2
        image_url (str, optional): URL de l'image à joindre
    
    Returns:
        tuple: (url_publication, tweet_id, result_data)
    """
    try:
        url = "https://api.x.com/2/tweets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        tweet_payload = {"text": texte_contenu[:280]}
        
        if image_url:
            media_id = upload_media_to_x(access_token, image_url)
            if media_id:
                tweet_payload["media"] = {"media_ids": [media_id]}
                current_app.logger.info(f"Image ajoutée à la publication X, media_id: {media_id}")
            else:
                current_app.logger.warning(f"Échec du téléchargement de l'image, publication du texte seulement")

        current_app.logger.info(f"Publication sur X: {texte_contenu[:100]}... (image: {bool(image_url)})")

        response = requests.post(url, headers=headers, json=tweet_payload, timeout=30)

        if response.status_code not in [200, 201]:
            error_detail = response.json().get('detail', response.text)
            current_app.logger.error(f"Erreur API X: {response.status_code} - {error_detail}")
            return None, None, f"Erreur {response.status_code}: {error_detail}"

        tweet_data = response.json()
        tweet_id = tweet_data.get('data', {}).get('id')
        url_publication = f"https://x.com/i/status/{tweet_id}" if tweet_id else None

        current_app.logger.info(f"Publication X réussie: {url_publication}")

        return url_publication, tweet_id, tweet_data

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur réseau API X: {str(e)}")
        return None, None, f"Erreur réseau: {str(e)}"


def upload_media_to_x(access_token, image_url):
    """
    Télécharge un média sur X et retourne son media_id
    
    Args:
        access_token (str): Token d'accès
        image_url (str): URL de l'image à télécharger
    
    Returns:
        str: media_id ou None en cas d'erreur
    """
    try:

        current_app.logger.info(f"Téléchargement de l'image: {image_url}")
        image_response = requests.get(image_url, timeout=30)
        
        if image_response.status_code != 200:
            current_app.logger.error(f"Échec téléchargement image: {image_response.status_code}")
            return None

        init_url = "https://upload.twitter.com/1.1/media/upload.json"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

     
        files = {
            "media": image_response.content
        }

        upload_response = requests.post(init_url, headers=headers, files=files, timeout=30)

        if upload_response.status_code == 200:
            media_data = upload_response.json()
            return media_data.get('media_id_string')
        else:
            current_app.logger.error(f"Échec upload média X: {upload_response.status_code} - {upload_response.text}")
            return None

    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'upload du média: {str(e)}")
        return None


def upload_media_to_x_advanced(access_token, image_url):
    """
    Version avancée de l'upload de média avec les 3 étapes X API
    """
    try:
        image_response = requests.get(image_url, timeout=30)
        if image_response.status_code != 200:
            return None

        file_data = image_response.content
        total_bytes = len(file_data)


        init_url = "https://upload.twitter.com/1.1/media/upload.json"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        init_params = {
            "command": "INIT",
            "media_type": "image/jpeg/png", 
            "total_bytes": total_bytes
        }

        init_response = requests.post(init_url, headers=headers, params=init_params)
        if init_response.status_code != 200:
            return None

        media_id = init_response.json().get('media_id_string')

        append_params = {
            "command": "APPEND",
            "media_id": media_id,
            "segment_index": 0
        }

        files = {"media": file_data}
        append_response = requests.post(init_url, headers=headers, params=append_params, files=files)

        if append_response.status_code != 200:
            return None

        finalize_params = {
            "command": "FINALIZE",
            "media_id": media_id
        }

        finalize_response = requests.post(init_url, headers=headers, params=finalize_params)
        if finalize_response.status_code == 200:
            return media_id
        else:
            return None

    except Exception as e:
        current_app.logger.error(f"Erreur upload média avancé: {str(e)}")
        return None
    

def delete_publication_from_x(tweet_id, access_token):

    try:
        url = f"https://api.x.com/2/tweets/{tweet_id}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        current_app.logger.info(f"Tentative de suppression du tweet ID: {tweet_id}")

        response = requests.delete(url, headers=headers, timeout=20)

        if response.status_code in [200, 204]:
            current_app.logger.info(f"Tweet supprimé avec succès (ID: {tweet_id})")
            return True, f"Tweet {tweet_id} supprimé avec succès."

        try:
            error_detail = response.json().get('detail', response.text)
        except Exception:
            error_detail = response.text
        
        current_app.logger.error(f"Erreur suppression X: {response.status_code} - {error_detail}")
        return False, f"Erreur {response.status_code}: {error_detail}"

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur réseau lors de la suppression du tweet: {str(e)}")
        return False, f"Erreur réseau: {str(e)}"


def get_tweet_metrics(tweet_id, access_token):
    """
    Récupère les métriques d'un tweet avec plusieurs tentatives
    
    Args:
        tweet_id (str): ID du tweet
        access_token (str): Token d'accès OAuth2
    
    Returns:
        dict: {'views': int, 'likes': int, 'retweets': int} ou None
    
    IMPORTANT: Les impressions (vues) nécessitent OAuth 1.0a avec l'accès au compte propriétaire.
    Avec OAuth 2.0, seules les métriques publiques sont disponibles (likes, RT, replies, quotes).
    """
    try:
        url = f"https://api.x.com/2/tweets/{tweet_id}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Demander TOUS les champs de métriques disponibles
        params = {
            "tweet.fields": "public_metrics,non_public_metrics,organic_metrics,promoted_metrics"
        }
        
        current_app.logger.info(f"📊 Récupération des métriques du tweet: {tweet_id}")
        
        response = requests.get(url, headers=headers, params=params, timeout=20)
        
        if response.status_code != 200:
            try:
                error_detail = response.json().get('detail', response.text)
            except:
                error_detail = response.text
            current_app.logger.error(f"❌ Erreur récupération métriques: {response.status_code} - {error_detail}")
            
            # Si erreur 403, c'est probablement un problème de permissions
            if response.status_code == 403:
                current_app.logger.warning(
                    " Erreur 403: Les métriques étendues nécessitent OAuth 1.0a "
                    "ou un accès élevé à l'API. Seules les métriques publiques sont disponibles."
                )
            
            return None
        
        tweet_data = response.json()
        data = tweet_data.get('data', {})
        
        # Essayer différentes sources de métriques
        public_metrics = data.get('public_metrics', {})
        organic_metrics = data.get('organic_metrics', {})
        non_public_metrics = data.get('non_public_metrics', {})
        promoted_metrics = data.get('promoted_metrics', {})
        
        # Log pour debug
        current_app.logger.debug(f"📊 Métriques disponibles pour {tweet_id}:")
        current_app.logger.debug(f"   - public_metrics: {public_metrics}")
        if organic_metrics:
            current_app.logger.debug(f"   - organic_metrics: {organic_metrics}")
        if non_public_metrics:
            current_app.logger.debug(f"   - non_public_metrics: {non_public_metrics}")
        if promoted_metrics:
            current_app.logger.debug(f"   - promoted_metrics: {promoted_metrics}")
        
        # Impressions: essayer plusieurs sources (ordre de préférence)
        views = 0
        
        # 1. Organic metrics (meilleure source)
        if organic_metrics and 'impression_count' in organic_metrics:
            views = organic_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis organic_metrics: {views}")
        
        # 2. Non-public metrics
        elif non_public_metrics and 'impression_count' in non_public_metrics:
            views = non_public_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis non_public_metrics: {views}")
        
        # 3. Promoted metrics
        elif promoted_metrics and 'impression_count' in promoted_metrics:
            views = promoted_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis promoted_metrics: {views}")
        
        # 4. Public metrics (peu probable)
        elif public_metrics and 'impression_count' in public_metrics:
            views = public_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis public_metrics: {views}")
        
        else:
            current_app.logger.warning(
                f"⚠️ Aucune métrique d'impression disponible pour {tweet_id}. "
                "Cela est normal avec OAuth 2.0 Basic Access. "
                "Pour obtenir les impressions, vous devez utiliser OAuth 1.0a."
            )
        
        result = {
            'views': views,
            'likes': public_metrics.get('like_count', 0),
            'retweets': public_metrics.get('retweet_count', 0),
            'replies': public_metrics.get('reply_count', 0),
            'quotes': public_metrics.get('quote_count', 0),
            'bookmarks': public_metrics.get('bookmark_count', 0)
        }
        
        current_app.logger.info(
            f"✅ Métriques récupérées pour {tweet_id}: "
            f"{result['views']} vues, {result['likes']} likes, "
            f"{result['retweets']} RT, {result['quotes']} quotes"
        )
        
        return result
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"❌ Erreur réseau récupération métriques: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"❌ Erreur inattendue récupération métriques: {str(e)}", exc_info=True)
        return None