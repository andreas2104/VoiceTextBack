from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            identity = get_jwt_identity() or {}
            role = identity.get("role")
            if role not in roles:
                return jsonify({"error": "Accès refusé"}), 403
            return fn(*args, **kwargs)
        return decorated
    return wrapper


