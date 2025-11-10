import requests
from flask import current_app
import base64


def publish_to_x_api(texte_contenu, access_token, image_url=None):

    print("acc", access_token)
    try:
        url = "https://api.x.com/2/tweets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        tweet_payload = {"text": texte_contenu[:280]}
        
        if image_url:
            media_id = upload_image_to_x(access_token, image_url)
            if media_id:
                tweet_payload["media"] = {"media_ids": [media_id]}
                # current_app.logger.info(f" Image ajoutée à la publication X, media_id: {media_id}")
            else:
                current_app.logger.warning(f" Échec du téléchargement de l'image, publication du texte seulement")

        # raise Exception("hihihihihih")

        current_app.logger.info(f"Publication sur X: {texte_contenu[:100]}... (image: {bool(image_url)})")

        response = requests.post(url, headers=headers, json=tweet_payload, timeout=30)

        if response.status_code not in [200, 201]:
            error_detail = response.json().get('detail', response.text)
            current_app.logger.error(f" Erreur API X: {response.status_code} - {error_detail}")
            return None, None, f"Erreur {response.status_code}: {error_detail}"

        tweet_data = response.json()
        tweet_id = tweet_data.get('data', {}).get('id')
        url_publication = f"https://x.com/i/status/{tweet_id}" if tweet_id else None

        current_app.logger.info(f" Publication X réussie: {url_publication}")

        return url_publication, tweet_id, tweet_data

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f" Erreur réseau API X: {str(e)}")
        return None, None, f"Erreur réseau: {str(e)}"


def upload_image_to_x(access_token, image_url):
    try:
        [prefix, image_data] = image_url.split(',', maxsplit=1)
        print(f"[]sample_0: {image_data[0:100]}...")
        [_, ty] = prefix.split(":")
        [media_type, _] = ty.split(";")
        
        image_bytes = base64.b64decode(image_data)

        url = "https://api.x.com/2/media/upload"
        headers = {
            # "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        files = {'media': image_bytes, 
            
        }
        data = {
             'media_type':  media_type,
            'media_category': "tweet_image"
        }
       
        # print("OOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
        upload_response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        # print("IIIIIIIIIIIIIIIIIIIIIIIi")

        print(f"status, {upload_response.status_code}")
        print(f"status texte, {upload_response.json()}")
        
        
        if upload_response.status_code in [200, 201]:
            media_id = upload_response.json().get("data", {}).get("id", None)
            current_app.logger.info(f"Upload reussi, media_id:{media_id}")
            return media_id

        else :
            current_app.logger.error(f"Erreur  upload image: {upload_response.status_code}-{upload_response.text}")
            print("hahahhahha")
            return None
    except requests.HTTPError as e:
        print("HTTP Error", e)
        raise e

    except Exception as e:
        print("exception", type(e).__name__)
        current_app.logger.error(f"Erreur upload image: {repr(e)}")
        print("hahahaha")
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
    try:
        url = f"https://api.x.com/2/tweets/{tweet_id}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
    
        params = {
            "tweet.fields": "public_metrics,non_public_metrics,organic_metrics,promoted_metrics"
        }
        
        current_app.logger.info(f"Récupération des métriques du tweet: {tweet_id}")
        
        response = requests.get(url, headers=headers, params=params, timeout=20)
        
        if response.status_code != 200:
            try:
                error_detail = response.json().get('detail', response.text)
            except:
                error_detail = response.text
            current_app.logger.error(f" Erreur récupération métriques: {response.status_code} - {error_detail}")
            
            if response.status_code == 403:
                current_app.logger.warning(
                    " Erreur 403: Les métriques étendues nécessitent OAuth 1.0a "
                    "ou un accès élevé à l'API. Seules les métriques publiques sont disponibles."
                )
            
            return None
        
        tweet_data = response.json()
        data = tweet_data.get('data', {})
        
   
        public_metrics = data.get('public_metrics', {})
        organic_metrics = data.get('organic_metrics', {})
        non_public_metrics = data.get('non_public_metrics', {})
        promoted_metrics = data.get('promoted_metrics', {})
        
    
        current_app.logger.debug(f" Métriques disponibles pour {tweet_id}:")
        current_app.logger.debug(f"   - public_metrics: {public_metrics}")
        if organic_metrics:
            current_app.logger.debug(f"   - organic_metrics: {organic_metrics}")
        if non_public_metrics:
            current_app.logger.debug(f"   - non_public_metrics: {non_public_metrics}")
        if promoted_metrics:
            current_app.logger.debug(f"   - promoted_metrics: {promoted_metrics}")
        
        views = 0
        
        
        if organic_metrics and 'impression_count' in organic_metrics:
            views = organic_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis organic_metrics: {views}")
     
        elif non_public_metrics and 'impression_count' in non_public_metrics:
            views = non_public_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis non_public_metrics: {views}")
        

        elif promoted_metrics and 'impression_count' in promoted_metrics:
            views = promoted_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis promoted_metrics: {views}")
        
     
        elif public_metrics and 'impression_count' in public_metrics:
            views = public_metrics.get('impression_count', 0)
            current_app.logger.debug(f"   ✓ Vues depuis public_metrics: {views}")
        
        else:
            current_app.logger.warning(
                f" Aucune métrique d'impression disponible pour {tweet_id}. "
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
            f" Métriques récupérées pour {tweet_id}: "
            f"{result['views']} vues, {result['likes']} likes, "
            f"{result['retweets']} RT, {result['quotes']} quotes"
        )
        
        return result
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur réseau récupération métriques: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"Erreur inattendue récupération métriques: {str(e)}", exc_info=True)
        return None