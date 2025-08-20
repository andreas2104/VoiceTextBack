from app.extensions import db
from datetime import datetime
import json

class Prompt(db.Model):
  __tablename__ = "prompt"

  id = db.Column(db.Integer, primary_key=True)
  id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable = True)
  nom_prompt = db.Column(db.String(100), nullable=False)
  texte_prompt = db.Column(db.Text, nullable=False)
  parametres = db.Column(db.JSON, nullable=True)
  public = db.Column(db.Boolean, default=True, nullable=False)
  utilisation_count = db.Column(db.Integer, default=0, nullable=False)
  date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
  date_modification = db.Column(db.DateTime,nullable=True)

  def __repr__(self):
    return f"<Prompt {self.id}: {self.nom_prompt}>"
  # migration a refaire