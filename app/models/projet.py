from app.extensions import db
from datetime import datetime
from sqlalchemy import Enum
import enum
import json


class TypeStatusEnum(enum.Enum):
   draft = "draft"
   active = "active"
   archived = "archived"

class Projet(db.Model):
   __tablename__ = "projets"

   id = db.Column(db.Integer, primary_key=True)
   id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
   nom_projet = db.Column(db.String(100), nullable=False)
   description = db.Column(db.String(300), nullable=True)
   date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
   date_modification = db.Column(db.DateTime, nullable=True)
   status = db.Column(db.Enum(TypeStatusEnum), default=TypeStatusEnum.draft, nullable=False)
   configuration =  db.Column(db.JSON, nullable=True)
   def __repr__(self):
      return f"<Projet {self.id}: {self.nom_projet} - {self.status}>"