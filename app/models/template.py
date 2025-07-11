from app.extensions import db
import json

class Template(db.Model):
  __table__="templates"

  id = db.Column(db.Integer, primary_key=True)
  id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
  nom_template =  db.Column(db.String(100), nullable=False)
  structure =  db.Column(db.String(300), nullable=False)
  variables = db.Column(db.JSON, nullable=True)
  type_sortie = db.Column(db.String(50), nullable=False)
  public = db.Column(db.Boolean, default=True, nullable=False)
  date_creation = db.Column(db.DateTime, nullable=True)

  def __repr__(self):
    return f"<Template {self.id}: {self.nom_template}>"