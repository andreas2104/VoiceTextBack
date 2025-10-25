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
