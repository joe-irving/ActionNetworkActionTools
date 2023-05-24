"""empty message

Revision ID: 51160d2f14d6
Revises: 950056e311c2
Create Date: 2023-05-24 18:12:11.639288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '51160d2f14d6'
down_revision = '950056e311c2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rolling_emailer', schema=None) as batch_op:
        batch_op.add_column(sa.Column('targets_each', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rolling_emailer', schema=None) as batch_op:
        batch_op.drop_column('targets_each')

    # ### end Alembic commands ###
