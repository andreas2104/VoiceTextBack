from functools import wraps
from app.utils.identity import get_identity
from flask import jsonify
from flask_jwt_extended import jwt_required

def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            identity = get_identity() or {}
            role = identity.get("role")
            if role not in roles:
                return jsonify({"error": "Accès refusé"}), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper


