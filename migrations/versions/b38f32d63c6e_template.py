"""template

Revision ID: b38f32d63c6e
Revises: 4c687c30cccf
Create Date: 2025-07-14 08:52:17.383743

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b38f32d63c6e'
down_revision = '4c687c30cccf'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Crée le nouveau type ENUM si non existant
    sa.Enum('draft', 'active', 'archived', name='typestatusenum').create(op.get_bind(), checkfirst=True)

    # 2. Change le type de la colonne en spécifiant clairement le cast
    op.execute("ALTER TABLE projets ALTER COLUMN status TYPE typestatusenum USING status::text::typestatusenum")


def downgrade():
    # 1. Crée l'ancien type enum si nécessaire
    postgresql.ENUM('draft', 'active', 'archived', name='status').create(op.get_bind(), checkfirst=True)

    # 2. Recast vers l'ancien type
    op.execute("ALTER TABLE projets ALTER COLUMN status TYPE status USING status::text::status")

    # 3. Supprime le nouveau type ENUM
    sa.Enum('draft', 'active', 'archived', name='typestatusenum').drop(op.get_bind(), checkfirst=True)
