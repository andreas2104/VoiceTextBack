from app.models.utilisateur import Utilisateur, Token
from datetime import datetime, timedelta
from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError


def store_token(utilisateur_id: int, provider: str, access_token: str, refresh_token: str, expires_in: int) -> Token:
    """
    Stocke ou met à jour un token d'authentification
    
    Args:
        utilisateur_id: ID de l'utilisateur
        provider: Fournisseur d'authentification (google, facebook, etc.)
        access_token: Token d'accès
        refresh_token: Token de rafraîchissement
        expires_in: Durée de validité en secondes
    
    Returns:
        Token: L'objet token créé ou mis à jour
        
    Raises:
        ValueError: Si les paramètres requis sont invalides
        Exception: En cas d'erreur base de données
    """
    # Validation des paramètres
    if not all([utilisateur_id, provider, access_token]):
        raise ValueError("utilisateur_id, provider et access_token sont obligatoires")
    
    if expires_in <= 0:
        raise ValueError("expires_in doit être positif")

    try:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        token = Token.query.filter_by(
            utilisateur_id=utilisateur_id,
            provider=provider
        ).first()

        if token:
            token.access_token = access_token
            if refresh_token:
                token.refresh_token = refresh_token
            token.expires_at = expires_at
            token.updated_at = datetime.utcnow() 
        else:
            token = Token(
                utilisateur_id=utilisateur_id,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
            )
            db.session.add(token)

        db.session.commit()
        return token

    except SQLAlchemyError as e:
        db.session.rollback()
        raise Exception(f"Erreur lors du stockage du token: {str(e)}")