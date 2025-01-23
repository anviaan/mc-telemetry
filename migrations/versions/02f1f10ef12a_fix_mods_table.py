"""fix mods table

Revision ID: 02f1f10ef12a
Revises: 1ef1a20993ab
Create Date: 2025-01-22 16:54:32.571497

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '02f1f10ef12a'
down_revision = '1ef1a20993ab'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('mods', schema=None) as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('updated_at')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('mods', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', mysql.DATETIME(), nullable=True))
        batch_op.add_column(sa.Column('created_at', mysql.DATETIME(), nullable=True))

    # ### end Alembic commands ###
