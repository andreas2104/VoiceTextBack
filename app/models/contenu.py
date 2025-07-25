from app.extensions import db
from datetime import datetime
import enum

class TypeContenuEnum(enum.Enum):
    text = "text"
    video = "video"
    image = "image"

class Contenu(db.Model):
    __tablename__ = "contenu"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    id_model = db.Column(db.Integer, db.ForeignKey('model_ia.id'), nullable=False)
    id_template = db.Column(db.Integer, db.ForeignKey('templates.id'), nullable=True)
    id_prompt = db.Column(db.Integer, db.ForeignKey('prompt.id'), nullable=True)

    titre = db.Column(db.String(255), nullable=True)
    type_contenu = db.Column(db.Enum(TypeContenuEnum), default=TypeContenuEnum.text, nullable=False)
    texte = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(300), nullable=True)
    meta = db.Column(db.JSON, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Contenu {self.id}: {self.titre}>"
