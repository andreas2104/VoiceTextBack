"""Add multimodal to TypeContenuEnum

Revision ID: b4c0711f137c
Revises: c5d321c8e60d
Create Date: 2025-11-15 15:58:13.175897

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c0711f137c'
down_revision = 'c5d321c8e60d'
branch_labels = None
depends_on = None


def upgrade():
    # Vérifier si la valeur existe déjà avant de l'ajouter
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'multimodal' 
                AND enumtypid = 'typecontenuenum'::regtype
            ) THEN
                ALTER TYPE typecontenuenum ADD VALUE 'multimodal';
            END IF;
        END $$;
    """)
def downgrade():
    pass
