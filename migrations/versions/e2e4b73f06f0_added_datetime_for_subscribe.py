"""added datetime for subscribe

Revision ID: e2e4b73f06f0
Revises: 7e71742293d7
Create Date: 2020-04-18 23:13:28.821026

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2e4b73f06f0'
down_revision = '7e71742293d7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('subscribe', sa.Column('last_update', sa.DateTime(), nullable=True))
    op.execute("UPDATE subscribe SET last_update = NOW()")
    op.alter_column('subscribe', 'last_update', nullable=False)
    op.add_column('subscribe', sa.Column('subscribed_datetime', sa.DateTime(), nullable=True))
    op.execute("UPDATE subscribe SET subscribed_datetime = NOW()")
    op.alter_column('subscribe', 'subscribed_datetime', nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('subscribe', 'subscribed_datetime')
    op.drop_column('subscribe', 'last_update')
    # ### end Alembic commands ###
