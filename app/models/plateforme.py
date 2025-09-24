# app/models/plateforme.py
from app.extensions import db
from datetime import datetime
from enum import Enum

class TypePlateformeEnum(Enum):
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"

class StatutConnexionEnum(Enum):
    CONNECTE = "connecte"
    DECONNECTE = "deconnecte"
    EXPIRE = "expire"
    ERREUR = "erreur"

class Plateforme(db.Model):
    __tablename__ = 'plateformes'
    
    # Clés primaires et étrangères
    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    
    # Informations de la plateforme
    nom_plateforme = db.Column(db.Enum(TypePlateformeEnum), nullable=False)
    nom_compte = db.Column(db.String(100), nullable=False)
    id_compte_externe = db.Column(db.String(100))
    
    # Tokens et authentification
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expiration = db.Column(db.DateTime)
    statut_connexion = db.Column(db.Enum(StatutConnexionEnum), default=StatutConnexionEnum.DECONNECTE)
    
    # Paramètres et limites
    permissions_accordees = db.Column(db.JSON, default=list)
    limite_posts_jour = db.Column(db.Integer, default=25)
    posts_publies_aujourd_hui = db.Column(db.Integer, default=0)
    
    # Dates de suivi
    derniere_publication = db.Column(db.DateTime)
    derniere_synchronisation = db.Column(db.DateTime)
    
    # Statut et dates système
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relations
    publications = db.relationship('Publication', backref='plateforme_ref', lazy=True)

    # Contrainte d'unicité : un utilisateur ne peut avoir qu'une seule connexion par plateforme
    __table_args__ = (
        db.UniqueConstraint('id_utilisateur', 'nom_plateforme', name='unique_user_platform'),
    )

    def __repr__(self):
        return f'<Plateforme {self.nom_plateforme.value} - {self.nom_compte}>'

    def to_dict(self):
        """Convertit l'objet en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'id_utilisateur': self.id_utilisateur,
            'nom_plateforme': self.nom_plateforme.value,
            'nom_compte': self.nom_compte,
            'id_compte_externe': self.id_compte_externe,
            'statut_connexion': self.statut_connexion.value,
            'token_expiration': self.token_expiration.isoformat() if self.token_expiration else None,
            'permissions_accordees': self.permissions_accordees or [],
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
        if self.nom_plateforme == TypePlateformeEnum.FACEBOOK:
            return {
                'base_url': 'https://graph.facebook.com/v18.0',
                'endpoints': {
                    'page_posts': f'/{self.id_compte_externe}/feed',
                    'page_info': f'/{self.id_compte_externe}',
                },
                'required_permissions': ['pages_manage_posts', 'pages_read_engagement']
            }
        elif self.nom_plateforme == TypePlateformeEnum.LINKEDIN:
            return {
                'base_url': 'https://api.linkedin.com/v2',
                'endpoints': {
                    'shares': '/shares',
                    'ugcPosts': '/ugcPosts'
                },
                'required_permissions': ['w_member_social']
            }
        return {}

    def incrementer_posts_aujourd_hui(self):
        """Incrémente le compteur de posts du jour"""
        self.posts_publies_aujourd_hui += 1
        self.derniere_publication = datetime.utcnow()

    @classmethod
    def get_by_user_and_platform(cls, user_id, platform_type):
        """Récupère une plateforme par utilisateur et type"""
        return cls.query.filter_by(
            id_utilisateur=user_id,
            nom_plateforme=platform_type
        ).first()

    @classmethod
    def get_active_platforms(cls, user_id):
        """Récupère toutes les plateformes actives d'un utilisateur"""
        return cls.query.filter_by(
            id_utilisateur=user_id,
            actif=True
        ).all()