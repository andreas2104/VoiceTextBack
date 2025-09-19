# from flask import Blueprint, request, jsonify, current_app
# import jwt
# import datetime
# from werkzeug.security import check_password_hash
# from  models import Utilisateur, TypeCompteEnum


# main = Blueprint('main', __name__)

# @main.route('/utilisateurs/login', methods=['POST'])
# def login():
#     """
#     Vérifie les informations de connexion et génère un JWT.
#     """
#     auth = request.json
#     if not auth or not auth.get('email') or not auth.get('password'):
#         return jsonify({"error": "Missing email or password"}), 400

#     email = auth.get('email')
#     mot_de_passe = auth.get('password')

#     utilisateur = Utilisateur.query.filter_by(email=email).first()

#     if not utilisateur or not check_password_hash(utilisateur.mot_de_passe, mot_de_passe):
#         return jsonify({"error": "Invalid email or password"}), 401

#     token_payload = {
#         'id': utilisateur.id,
#         'email': utilisateur.email,
#         'type_compte': utilisateur.type_compte.name,
#         'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
#     }

#     token = jwt.encode(
#         token_payload, 
#         current_app.config['SECRET_KEY'], 
#         algorithm='HS256'
#     )
#     return jsonify({"token": token}), 200

# @main.route('/protected', methods=['GET'])
# def protected():
#     """
#     Route protégée qui nécessite un JWT valide.
#     """
#     token = request.headers.get('Authorization')
#     if not token or not token.startswith("Bearer "):
#         return jsonify({"error": "Token is missing or malformed"}), 401
    
#     token = token.split(" ")[1]

#     try:
#         data = jwt.decode(
#             token, 
#             current_app.config['SECRET_KEY'], 
#             algorithms=['HS256']
#         )
#         current_user_email = data['email']
#         current_user_id = data['id']
#         return jsonify({
#             "message": f"Bonjour, {current_user_email} (ID: {current_user_id})! Bienvenue dans la zone protégée."
#         }), 200
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Token has expired"}), 401
#     except jwt.InvalidTokenError:
#         return jsonify({"error": "Invalid token"}), 401