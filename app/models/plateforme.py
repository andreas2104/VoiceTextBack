from datetime import datetime, timedelta
from app.extensions import db
from sqlalchemy import JSON

class PlateformeConfig(db.Model):
    __tablename__ = 'plateforme_config'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), unique=True, nullable=False)
    config = db.Column(JSON, default=dict)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'config': self.config,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_client_id(self):
        return self.config.get('client_id')
    
    def get_client_secret(self):
        return self.config.get('client_secret')
    
    def get_scopes(self):
        return self.config.get('scopes', [])
    
    def is_active(self):
        return self.active
    
    def update_config(self, new_config):
        self.config.update(new_config)
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_active_platforms(cls):
        return cls.query.filter_by(active=True).all()
    
    @classmethod
    def get_platform_by_name(cls, nom):
        return cls.query.filter_by(nom=nom, active=True).first()


class UtilisateurPlateforme(db.Model):
    __tablename__ = 'utilisateur_plateforme'
    
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    plateforme_id = db.Column(db.Integer, db.ForeignKey('plateforme_config.id'), nullable=False)
    external_id = db.Column(db.String(200), nullable=True)
    access_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    meta = db.Column(JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    utilisateur = db.relationship('Utilisateur', backref=db.backref('plateformes', lazy=True))
    plateforme = db.relationship('PlateformeConfig', backref=db.backref('utilisateurs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'utilisateur_id': self.utilisateur_id,
            'plateforme_id': self.plateforme_id,
            'external_id': self.external_id,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'meta': self.meta,
            'plateforme_nom': self.plateforme.nom if self.plateforme else None,
            'token_valide': self.is_token_valid()
        }
    
    def is_token_valid(self):
        if not self.token_expires_at or not self.access_token:
            return False
        return self.token_expires_at > datetime.utcnow()
    
    def update_token(self, access_token, expires_in=None, expires_at=None):
        self.access_token = access_token
        if expires_at:
            self.token_expires_at = expires_at
        elif expires_in:
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_user_platform(cls, utilisateur_id, plateforme_nom):
        return cls.query.join(PlateformeConfig).filter(
            cls.utilisateur_id == utilisateur_id,
            PlateformeConfig.nom == plateforme_nom
        ).first()


class OAuthState(db.Model):
    __tablename__ = 'oauth_state'
    
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(255), unique=True, nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    plateforme_id = db.Column(db.Integer, db.ForeignKey('plateforme_config.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

    utilisateur = db.relationship('Utilisateur', backref=db.backref('oauth_states', lazy=True))
    plateforme = db.relationship('PlateformeConfig', backref=db.backref('oauth_states', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'state': self.state,
            'utilisateur_id': self.utilisateur_id,
            'plateforme_id': self.plateforme_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'used': self.used
        }
    
    def is_valid(self, timeout_minutes=10):
        if self.used:
            return False
        expiration_time = self.created_at + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() < expiration_time
    
    def mark_as_used(self):
        self.used = True
