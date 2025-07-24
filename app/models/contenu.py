from app.extensions import db
from datetime import datetime
import enum
import json


class TypeContenuEnum(enum.Enum):
  text="text"
  video="video"
  image="image"

class Contenu(db.Model):
  __tablename__ = "contenu"

  id_contenu = db.Column(db.Integer, primary_key=True)
  id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
  id_modele = db.Column(db.Integer, db.ForeignKey('model_ia.id'))
  titre = db.Column(db.String(255), nullable=True)
  type_contenu = db.Column(db.Enum(TypeContenuEnum), default=TypeContenuEnum.text, nullable=False)
  texte = db.Column(db.String, nullable=True)
  image_url = db.Column(db.String(300), nullable=True)
  meta = db.Column(db.JSON, nullable= True)
  date_creation = db.Column(db.DateTime, default=datetime.utcnow)

def __repr__(self):
  return f"<Prompt {self.id}: {self.nom_prompt}"
  