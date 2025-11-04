from app.extensions import db
from datetime import datetime, timezone
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
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    id_contenu = db.Column(db.Integer, db.ForeignKey('contenu.id', ondelete='CASCADE'), nullable=False)
    plateforme = db.Column(db.String(50), nullable=False, default='x')
    titre_publication = db.Column(db.String(255), nullable=False)
    statut = db.Column(db.Enum(StatutPublicationEnum), default=StatutPublicationEnum.brouillon)
    date_programmee = db.Column(db.DateTime)
    date_publication = db.Column(db.DateTime)
    url_publication = db.Column(db.String(500))
    id_externe = db.Column(db.String(100))
    parametres_publication = db.Column(db.JSON, default={})
    message_erreur = db.Column(db.Text)
    nombre_vues = db.Column(db.Integer, default=0)
    nombre_likes = db.Column(db.Integer, default=0)
    nombre_partages = db.Column(db.Integer, default=0)
    
    # ✅ FIX : Stocker en UTC sans timezone info (naive datetime en UTC)
    date_creation = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    date_modification = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    contenu = db.relationship("Contenu", backref=db.backref("publications", lazy=True))
    
    def to_dict(self):
        """
        Convertit les dates stockées en naive UTC vers aware UTC pour l'API
        """
        def format_date(date_naive):
            if date_naive:
                # Si la date est naive, on considère qu'elle est en UTC
                if date_naive.tzinfo is None:
                    date_aware = date_naive.replace(tzinfo=timezone.utc)
                else:
                    date_aware = date_naive
                return date_aware.isoformat()
            return None
        
        return {
            'id': self.id,
            'id_utilisateur': self.id_utilisateur,
            'id_contenu': self.id_contenu,
            'plateforme': self.plateforme,
            'titre_publication': self.titre_publication,
            'statut': self.statut.value,
            'date_programmee': format_date(self.date_programmee),
            'date_publication': format_date(self.date_publication),
            'url_publication': self.url_publication,
            'id_externe': self.id_externe,
            'parametres_publication': self.parametres_publication,
            'message_erreur': self.message_erreur,
            'nombre_vues': self.nombre_vues,
            'nombre_likes': self.nombre_likes,
            'nombre_partages': self.nombre_partages,
            'date_creation': format_date(self.date_creation),
            'date_modification': format_date(self.date_modification),
            "contenu": {
                "texte": self.contenu.texte if self.contenu else None,
                "image_url": self.contenu.image_url if self.contenu else None
            }
        }