from app.extensions import db
from datetime import datetime
from enum import Enum

class StatutPublicationEnum(Enum):
    brouillon = "brouillon"
    programme = "programme"
    publie = "publie"
    echec = "echec"
    supprime = "supprime"

class Publication(db.Model):
    __tablename__ = 'publications'
    
    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    id_contenu = db.Column(db.Integer, db.ForeignKey('contenus.id'), nullable=False)
    id_plateforme = db.Column(db.Integer, db.ForeignKey('plateformes.id'), nullable=False)
    titre_publication = db.Column(db.String(255), nullable=False)
    statut = db.Column(db.Enum(StatutPublicationEnum), default=StatutPublicationEnum.brouillon)
    date_programmee = db.Column(db.DateTime)
    date_publication = db.Column(db.DateTime)
    url_publication = db.Column(db.String(500))
    id_externe = db.Column(db.String(100))  # ID sur la plateforme externe
    parametres_publication = db.Column(db.JSON, default={})
    message_erreur = db.Column(db.Text)
    nombre_vues = db.Column(db.Integer, default=0)
    nombre_likes = db.Column(db.Integer, default=0)
    nombre_partages = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'id_utilisateur': self.id_utilisateur,
            'id_contenu': self.id_contenu,
            'id_plateforme': self.id_plateforme,
            'titre_publication': self.titre_publication,
            'statut': self.statut.value,
            'date_programmee': self.date_programmee.isoformat() if self.date_programmee else None,
            'date_publication': self.date_publication.isoformat() if self.date_publication else None,
            'url_publication': self.url_publication,
            'id_externe': self.id_externe,
            'parametres_publication': self.parametres_publication,
            'message_erreur': self.message_erreur,
            'nombre_vues': self.nombre_vues,
            'nombre_likes': self.nombre_likes,
            'nombre_partages': self.nombre_partages,
            'date_creation': self.date_creation.isoformat(),
            'date_modification': self.date_modification.isoformat() if self.date_modification else None
        }