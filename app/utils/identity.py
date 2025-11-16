from flask_jwt_extended import get_jwt_identity


def get_identity() -> int | None:
    """
    In a protected endpoint, this will return the identity of the JWT that is
    accessing the endpoint. If no JWT is present due to
    ``jwt_required(optional=True)``, ``None`` is returned.

    :return:
        The identity of the JWT in the current request
    """
    identity = get_jwt_identity()
    return int (identity) if identity is not None else None

    