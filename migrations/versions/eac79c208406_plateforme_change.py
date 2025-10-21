"""plateforme change

Revision ID: eac79c208406
Revises: 4e45ab3b736d
Create Date: 2025-09-25 10:12:15.550459

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'eac79c208406'
down_revision = '4e45ab3b736d'
branch_labels = None
depends_on = None


def upgrade():
    # Vérifier si la table doit être renommée
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Supprimer les contraintes existantes
    with op.batch_alter_table('historiques', schema=None) as batch_op:
        batch_op.drop_constraint('historiques_id_plateforme_fkey', type_='foreignkey')

    with op.batch_alter_table('publications', schema=None) as batch_op:
        batch_op.drop_constraint('publications_id_plateforme_fkey', type_='foreignkey')

    # Renommer seulement si plateformes existe et plateforme_config n'existe pas
    if 'plateformes' in tables and 'plateforme_config' not in tables:
        op.rename_table('plateformes', 'plateforme_config')
    
    # Recréer les contraintes vers plateforme_config
    with op.batch_alter_table('historiques', schema=None) as batch_op:
        batch_op.create_foreign_key('historiques_id_plateforme_fkey', 'plateforme_config', ['id_plateforme'], ['id'])

    with op.batch_alter_table('publications', schema=None) as batch_op:
        batch_op.create_foreign_key('publications_id_plateforme_fkey', 'plateforme_config', ['id_plateforme'], ['id'])


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Supprimer les contraintes
    with op.batch_alter_table('publications', schema=None) as batch_op:
        batch_op.drop_constraint('publications_id_plateforme_fkey', type_='foreignkey')

    with op.batch_alter_table('historiques', schema=None) as batch_op:
        batch_op.drop_constraint('historiques_id_plateforme_fkey', type_='foreignkey')

    # Renommer seulement si plateforme_config existe et plateformes n'existe pas
    if 'plateforme_config' in tables and 'plateformes' not in tables:
        op.rename_table('plateforme_config', 'plateformes')
    
    # Recréer les contraintes originales
    with op.batch_alter_table('publications', schema=None) as batch_op:
        batch_op.create_foreign_key('publications_id_plateforme_fkey', 'plateformes', ['id_plateforme'], ['id'])

    with op.batch_alter_table('historiques', schema=None) as batch_op:
        batch_op.create_foreign_key('historiques_id_plateforme_fkey', 'plateformes', ['id_plateforme'], ['id'])