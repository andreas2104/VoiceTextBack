from app.extensions import db
from datetime import datetime
import json

class Template(db.Model):
  __tablename__="templates"

  id = db.Column(db.Integer, primary_key=True)
  id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
  nom_template =  db.Column(db.String(100), nullable=False)
  structure =  db.Column(db.String(300), nullable=False)
  variables = db.Column(db.JSON, nullable=True)
  type_sortie = db.Column(db.String(50), nullable=False)
  public = db.Column(db.Boolean, default=True, nullable=False)
  date_creation = db.Column(db.DateTime,default=datetime.utcnow ,nullable=True)

  def __repr__(self):
    return f"<Template {self.id}: {self.nom_template}>"
  
  def to_dict(self):
    return {
      'id': self.id,
      'nom_template':self.nom_template,
      'structure': self.structure,
      'variables': self.variables,
      'type_sortie': self.variables,
      'public': self.public,
      'date_creation': self.date_creation.isoformat() if self.date_creation else None,
    }
