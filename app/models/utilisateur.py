from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import Enum
import enum

class TypeCompteEnum(enum.Enum):
    admin = "admin"
    user = "user"
    free = "free"
    premium = "premium"

class Utilisateur(db.Model):
    __tablename__ = "utilisateurs"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=True) 
    photo = db.Column(db.String(255), nullable=True)  
    type_compte = db.Column(Enum(TypeCompteEnum), default=TypeCompteEnum.user, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actif = db.Column(db.Boolean, default=True, nullable=False)

def __repr__(self):
    return f"<Utilisateur {self.email}>"
def to_dict(self):
    return {
        "id": self.id,
        "nom": self.nom,
        "prenom": self.prenom,
        "email": self.email,
        "type_compte": self.type_compte.value if self.type_compte else None,
        "date_creation": self.date_creation.isoformat() if self.date_creation else None,
        "actif": self.actif,
        "photo": self.photo
    }

class Token(db.Model):
    __tablename__ = "tokens"

    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    provider = db.Column(db.String(50), nullable=False) 
    access_token = db.Column(db.String(500), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    utilisateur = db.relationship('Utilisateur', backref=db.backref('tokens', lazy='dynamic'))

    def __repr__(self):
        return f"<Token user={self.utilisateur_id} provider={self.provider}>"

    def to_dict(self):
        return {
            "id": self.id,
            "utilisateur_id": self.utilisateur_id,
            "provider": self.provider,  
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_valid(self):
        """Vérifie si le token est encore valide"""
        if not all([self.access_token, self.expires_at]):
            return False
        return datetime.utcnow() < self.expires_at

    def update_token(self, access_token, expires_in=None, expires_at=None):
        """Met à jour le token avec une nouvelle date d'expiration"""
        if not access_token:
            raise ValueError("Access token cannot be empty")
        
        self.access_token = access_token
        
        if expires_at:
            self.expires_at = expires_at
        elif expires_in:
            if expires_in <= 0:
                raise ValueError("expires_in must be positive")
            self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            raise ValueError("Either expires_in or expires_at must be provided")
        
        self.updated_at = datetime.utcnow()