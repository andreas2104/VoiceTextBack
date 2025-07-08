from app.extensions import db
from datetime import datetime
from sqlalchemy import Enum
import enum


class TypeCompteEnum(enum.Enum):
  admin = "admin"
  user = "user, free, premium"

class User(db.Model):
    _TableName_= "users"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=False)
    type_compte = db.Column(Enum(TypeCompteEnum), default=TypeCompteEnum.user, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actif = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User {self.email}> "
