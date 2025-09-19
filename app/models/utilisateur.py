from app.extensions import db
from datetime import datetime
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