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

        raise Exception("hihihihihih")

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
        # response = requests.get(image_url, timeout=30)
        # if response.status_code != 200:
        #     return None
        

        [prefix, image_data] = image_url.split(',', maxsplit=1)
        print(f"sample_0: {image_data[0:100]}...")
        [_, ty] = prefix.split(":")
        [media_type, _] = ty.split(";")
        
        image_bytes = base64.b64decode(image_data)

        url = "https://api.x.com/2/media/upload"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        files = {'media': image_bytes, 
            
            'media_type':  media_type,
            'media_category': "tweet_image"
        }

        upload_response = requests.post(url, headers=headers, files=files, timeout=30)

        print(f"status, {upload_response.status_code}")
        print(f"status texte, {upload_response.text}")
        
        
        if upload_response.status_code in [200, 201]:
            media_id = upload_response.json().get("media_id")
            current_app.logger.info(f"Upload reussi, media_id:{media_id}")
            return media_id

        else :
            current_app.logger.error(f"Erreur  upload image: {upload_response.status_code}-{upload_response.text}")
            print("hahahhahha")
            return None
        
    except Exception as e:
        current_app.logger.error(f"Erreur upload image: {repr(e)}")
        print("hahahaha")
        return None
        






# def upload_media_to_x_v2(access_token, image_data):
#     """
#     Télécharge un média sur X avec OAuth 2.0 (méthode chunked upload)
#     Compatible avec l'API v1.1 en utilisant Bearer token
    
#     Args:
#         access_token (str): Token d'accès OAuth 2.0
#         image_data (str): Image en base64 (format: data:image/jpeg;base64,...)
#                          OU URL de l'image
    
#     Returns:
#         str: media_id ou None en cas d'erreur
#     """
#     try:
        
#         if image_data.startswith('data:image'):
#             current_app.logger.info(f" Upload d'une image base64")
#             header, encoded = image_data.split(',', 1)
#             content_type = header.split(';')[0].split(':')[1]
#             image_bytes = base64.b64decode(encoded)
#         else:
#             current_app.logger.info(f" Téléchargement de l'image depuis URL: {image_data[:50]}...")
#             image_response = requests.get(image_data, timeout=30)
            
#             if image_response.status_code != 200:
#                 current_app.logger.error(f" Échec téléchargement image: {image_response.status_code}")
#                 return None
            
#             image_bytes = image_response.content
#             content_type = image_response.headers.get('Content-Type', 'image/jpeg')
        
#         total_bytes = len(image_bytes)
#         current_app.logger.info(f" Type: {content_type}, Taille: {total_bytes} bytes")


#         if total_bytes > 5 * 1024 * 1024:
#             current_app.logger.error(f" Image trop volumineuse: {total_bytes} bytes (max: 5MB)")
#             return None

#         headers = {
#             "Authorization": f"Bearer {access_token}"
#         }
#         base_url = "https://upload.twitter.com/1.1/media/upload.json"

#         # ÉTAPE 1: INIT
#         current_app.logger.info(f" Étape 1/3: Initialisation de l'upload...")
#         init_params = {
#             'command': 'INIT',
#             'total_bytes': total_bytes,
#             'media_type': content_type,
#             'media_category': 'tweet_image' 
#         }
        
#         init_response = requests.post(base_url, headers=headers, data=init_params, timeout=30)
        
#         if init_response.status_code != 202:
#             current_app.logger.error(f" Échec INIT: {init_response.status_code} - {init_response.text}")
#             return None
        
#         media_id = init_response.json().get('media_id_string')
#         current_app.logger.info(f" INIT réussi, media_id: {media_id}")

     
#         current_app.logger.info(f" Étape 2/3: Upload des données...")
        

#         chunk_size = 4 * 1024 * 1024  
#         segment_index = 0
        
#         for i in range(0, total_bytes, chunk_size):
#             chunk = image_bytes[i:i + chunk_size]
            
#             append_params = {
#                 'command': 'APPEND',
#                 'media_id': media_id,
#                 'segment_index': segment_index
#             }
            
#             files = {
#                 'media': chunk
#             }
            
#             append_response = requests.post(
#                 base_url, 
#                 headers=headers, 
#                 data=append_params, 
#                 files=files,
#                 timeout=60
#             )
            
#             if append_response.status_code not in [200, 201, 204]:
#                 current_app.logger.error(f" Échec APPEND segment {segment_index}: {append_response.status_code} - {append_response.text}")
#                 return None
            
#             segment_index += 1
#             current_app.logger.info(f" Segment {segment_index} uploadé")

#         current_app.logger.info(f" Étape 3/3: Finalisation de l'upload...")
#         finalize_params = {
#             'command': 'FINALIZE',
#             'media_id': media_id
#         }
        
#         finalize_response = requests.post(base_url, headers=headers, data=finalize_params, timeout=30)
        
#         if finalize_response.status_code not in [200, 201]:
#             current_app.logger.error(f" Échec FINALIZE: {finalize_response.status_code} - {finalize_response.text}")
#             return None
        
#         finalize_data = finalize_response.json()
#         processing_info = finalize_data.get('processing_info')
        
#         if processing_info:
#             state = processing_info.get('state')
#             current_app.logger.info(f"État du traitement: {state}")
            
#             if state == 'pending' or state == 'in_progress':
#                 import time
#                 check_after = processing_info.get('check_after_secs', 1)
#                 time.sleep(check_after)
                
#                 status_params = {
#                     'command': 'STATUS',
#                     'media_id': media_id
#                 }
#                 status_response = requests.get(base_url, headers=headers, params=status_params, timeout=30)
                
#                 if status_response.status_code == 200:
#                     status_data = status_response.json()
#                     processing_info = status_data.get('processing_info', {})
#                     state = processing_info.get('state')
                    
#                     if state == 'failed':
#                         error = processing_info.get('error', {})
#                         current_app.logger.error(f" Traitement échoué: {error}")
#                         return None

#         current_app.logger.info(f" Upload complet, media_id: {media_id}")
#         return media_id

#     except Exception as e:
#         current_app.logger.error(f" Erreur lors de l'upload du média: {str(e)}", exc_info=True)
#         return None



# def upload_media_to_x_simple(access_token, image_data):
#     """
#     Méthode simple d'upload (peut ne pas fonctionner avec OAuth 2.0)
#     Gardée pour référence
#     """
#     try:
#         if image_data.startswith('data:image'):
#             current_app.logger.info(f" Upload d'une image base64")
#             header, encoded = image_data.split(',', 1)
#             content_type = header.split(';')[0].split(':')[1]
#             image_bytes = base64.b64decode(encoded)
#         else:
#             current_app.logger.info(f" Téléchargement de l'image depuis URL: {image_data[:50]}...")
#             image_response = requests.get(image_data, timeout=30)
            
#             if image_response.status_code != 200:
#                 current_app.logger.error(f" Échec téléchargement image: {image_response.status_code}")
#                 return None
            
#             image_bytes = image_response.content
#             content_type = image_response.headers.get('Content-Type', 'image/jpeg')

#         current_app.logger.info(f" Type: {content_type}, Taille: {len(image_bytes)} bytes")

#         init_url = "https://upload.twitter.com/1.1/media/upload.json"
#         headers = {
#             "Authorization": f"Bearer {access_token}"
#         }

#         files = {
#             "media": ("image.jpg", image_bytes, content_type)
#         }

#         current_app.logger.info(f" Envoi de l'image à X...")
#         upload_response = requests.post(init_url, headers=headers, files=files, timeout=30)

#         if upload_response.status_code == 200:
#             media_data = upload_response.json()
#             media_id = media_data.get('media_id_string')
#             current_app.logger.info(f" Upload réussi, media_id: {media_id}")
#             return media_id
#         else:
#             current_app.logger.error(f" Échec upload média X: {upload_response.status_code} - {upload_response.text}")
#             return None

#     except Exception as e:
#         current_app.logger.error(f" Erreur lors de l'upload du média: {str(e)}", exc_info=True)
#         return None
# def upload_media_to_x_advanced(access_token, image_url):
#     """
#     Version avancée de l'upload de média avec les 3 étapes X API
#     MÉTHODE CHUNKED - Pour les images > 5 MB ou vidéos
#     """
#     try:
#         current_app.logger.info(f"Upload avancé de l'image: {image_url}")
#         image_response = requests.get(image_url, timeout=30)
#         if image_response.status_code != 200:
#             current_app.logger.error(f" Échec téléchargement: {image_response.status_code}")
#             return None

#         file_data = image_response.content
#         total_bytes = len(file_data)
        
 
#         content_type = image_response.headers.get('Content-Type', 'image/jpeg')
#         current_app.logger.info(f"Type MIME détecté: {content_type}, Taille: {total_bytes} bytes")

#         init_url = "https://upload.twitter.com/1.1/media/upload.json"
#         headers = {"Authorization": f"Bearer {access_token}"}
        
#         init_params = {
#             "command": "INIT",
#             "media_type": content_type,  
#             "total_bytes": total_bytes
#         }

#         current_app.logger.info("1️Initialisation de l'upload...")
#         init_response = requests.post(init_url, headers=headers, params=init_params, timeout=30)
        
#         if init_response.status_code != 202:
#             current_app.logger.error(f" Échec INIT: {init_response.status_code} - {init_response.text}")
#             return None

#         media_id = init_response.json().get('media_id_string')
#         current_app.logger.info(f" INIT réussi, media_id: {media_id}")

#         append_params = {
#             "command": "APPEND",
#             "media_id": media_id,
#             "segment_index": 0
#         }

#         files = {"media": file_data}
#         current_app.logger.info("2️Upload du contenu...")
#         append_response = requests.post(init_url, headers=headers, params=append_params, files=files, timeout=30)

#         if append_response.status_code not in [200, 201, 204]:
#             current_app.logger.error(f" Échec APPEND: {append_response.status_code} - {append_response.text}")
#             return None
        
#         current_app.logger.info(" APPEND réussi")

#         finalize_params = {
#             "command": "FINALIZE",
#             "media_id": media_id
#         }

#         current_app.logger.info("3️ Finalisation...")
#         finalize_response = requests.post(init_url, headers=headers, params=finalize_params, timeout=30)
        
#         if finalize_response.status_code == 201:
#             current_app.logger.info(f" Upload avancé terminé avec succès, media_id: {media_id}")
#             return media_id
#         else:
#             current_app.logger.error(f" Échec FINALIZE: {finalize_response.status_code} - {finalize_response.text}")
#             return None

#     except Exception as e:
#         current_app.logger.error(f" Erreur upload média avancé: {str(e)}", exc_info=True)
#         return None
        
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