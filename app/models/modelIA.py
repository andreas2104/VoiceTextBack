from app.extensions import db
import enum
import json


class TypeModelEnum(enum.Enum):
    text='text'
    image='image'
    multimodal='multimodal'

class ModelIA(db.Model):
    __tablename__ = "model_ia"

    id = db.Column(db.Integer, primary_key=True)
    nom_model = db.Column(db.String(100), nullable=False)
    type_model = db.Column(db.Enum(TypeModelEnum), default =TypeModelEnum.text, nullable=False)
    fournisseur = db.Column(db.String(100), nullable=False)
    api_endpoint = db.Column(db.String(200), nullable=False)
    parametres_default = db.Column(db.JSON, nullable=True)
    cout_par_token = db.Column(db.Float, nullable=False, default=0.0)
    actif = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ModelIA {self.id}: {self.nom_model} - {self.type_model} - {self.fournisseur}>"