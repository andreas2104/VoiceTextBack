from app.extensions import db
from datetime import datetime
from enum import Enum

class TypePlateformeEnum(Enum):
    facebook = "facebook"
    linkedin = "linkedin"
    instagram = "instagram"
    twitter = "twitter"

class StatutConnexionEnum(Enum):
    connecte = "connecte"
    deconnecte = "deconnecte"
    expire = "expire"
    erreur = "erreur"

class Plateforme(db.Model):
    __tablename__ = 'plateformes'
    
    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    nom_plateforme = db.Column(db.Enum(TypePlateformeEnum), nullable=False)
    nom_compte = db.Column(db.String(100))  
    id_compte_externe = db.Column(db.String(100))  
    
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expiration = db.Column(db.DateTime)
    statut_connexion = db.Column(db.Enum(StatutConnexionEnum), default=StatutConnexionEnum.deconnecte)
    
    permissions_accordees = db.Column(db.JSON, default=list)  
    parametres_publication = db.Column(db.JSON, default=dict) 
    
    limite_posts_jour = db.Column(db.Integer, default=25)  # Limite API
    posts_publies_aujourd_hui = db.Column(db.Integer, default=0)
    derniere_publication = db.Column(db.DateTime)
    derniere_synchronisation = db.Column(db.DateTime)
    

    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, onupdate=datetime.utcnow)

    publications = db.relationship('Publication', backref='plateforme', lazy=True, cascade='all, delete-orphan')
    historiques = db.relationship('Historique', backref='plateforme', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'id_utilisateur': self.id_utilisateur,
            'nom_plateforme': self.nom_plateforme.value,
            'nom_compte': self.nom_compte,
            'id_compte_externe': self.id_compte_externe,
            'statut_connexion': self.statut_connexion.value,
            'token_expiration': self.token_expiration.isoformat() if self.token_expiration else None,
            'permissions_accordees': self.permissions_accordees,
            'parametres_publication': self.parametres_publication,
            'limite_posts_jour': self.limite_posts_jour,
            'posts_publies_aujourd_hui': self.posts_publies_aujourd_hui,
            'derniere_publication': self.derniere_publication.isoformat() if self.derniere_publication else None,
            'derniere_synchronisation': self.derniere_synchronisation.isoformat() if self.derniere_synchronisation else None,
            'actif': self.actif,
            'date_creation': self.date_creation.isoformat(),
            'date_modification': self.date_modification.isoformat() if self.date_modification else None
        }

    def is_token_valid(self):
        """Vérifie si le token est encore valide"""
        if not self.access_token or not self.token_expiration:
            return False
        return datetime.utcnow() < self.token_expiration

    def peut_publier_aujourd_hui(self):
        """Vérifie si on peut encore publier aujourd'hui"""
        return self.posts_publies_aujourd_hui < self.limite_posts_jour

    def get_api_config(self):
        """Retourne la configuration API selon la plateforme"""
        if self.nom_plateforme == TypePlateformeEnum.facebook:
            return {
                'base_url': 'https://graph.facebook.com/v18.0',
                'endpoints': {
                    'page_posts': f'/{self.id_compte_externe}/feed',
                    'page_info': f'/{self.id_compte_externe}',
                    'insights': f'/{self.id_compte_externe}/insights'
                },
                'required_permissions': ['pages_manage_posts', 'pages_read_engagement'],
                'content_types': ['text', 'image', 'link', 'video']
            }
        elif self.nom_plateforme == TypePlateformeEnum.linkedin:
            return {
                'base_url': 'https://api.linkedin.com/v2',
                'endpoints': {
                    'shares': '/shares',
                    'ugcPosts': '/ugcPosts',
                    'organizations': f'/organizations/{self.id_compte_externe}'
                },
                'required_permissions': ['w_member_social', 'w_organization_social'],
                'content_types': ['text', 'image', 'article', 'video']
            }