from app.extensions import db
from datetime import datetime
from enum import Enum

class TypeActionEnum(Enum):
    creation = "creation"
    modification = "modification"
    suppression = "suppression"
    generation = "generation"
    publication = "publication"
    echec = "echec"

class Historique(db.Model):
    __tablename__ = 'historiques'
    
    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    id_contenu = db.Column(db.Integer, db.ForeignKey('contenu.id'))
    # Ligne corrigée ici : 'plateformes' devient 'plateforme_config'
    id_plateforme = db.Column(db.Integer, db.ForeignKey('plateforme_config.id'))
    type_action = db.Column(db.Enum(TypeActionEnum), nullable=False)
    description = db.Column(db.Text, nullable=False)
    donnees_avant = db.Column(db.JSON)
    donnees_apres = db.Column(db.JSON)
    ip_utilisateur = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    date_action = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'id_utilisateur': self.id_utilisateur,
            'id_contenu': self.id_contenu,
            'id_plateforme': self.id_plateforme,
            'type_action': self.type_action.value,
            'description': self.description,
            'donnees_avant': self.donnees_avant,
            'donnees_apres': self.donnees_apres,
            'ip_utilisateur': self.ip_utilisateur,
            'user_agent': self.user_agent,
            'date_action': self.date_action.isoformat()
        }
