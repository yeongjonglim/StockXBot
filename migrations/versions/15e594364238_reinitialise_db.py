"""Reinitialise db

Revision ID: 15e594364238
Revises: 
Create Date: 2020-04-18 08:39:23.545778

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15e594364238'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('company',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stock_code', sa.String(length=8), nullable=False),
    sa.Column('stock_name', sa.String(length=32), nullable=False),
    sa.Column('company_name', sa.String(length=128), nullable=False),
    sa.Column('company_site', sa.String(length=256), nullable=True),
    sa.Column('market', sa.String(length=32), nullable=False),
    sa.Column('sector', sa.String(length=64), nullable=False),
    sa.Column('last_done', sa.Float(), nullable=True),
    sa.Column('change_absolute', sa.Float(), nullable=True),
    sa.Column('change_percent', sa.Float(), nullable=True),
    sa.Column('opening', sa.Float(), nullable=True),
    sa.Column('closing', sa.Float(), nullable=True),
    sa.Column('buy_vol', sa.Integer(), nullable=True),
    sa.Column('sell_vol', sa.Integer(), nullable=True),
    sa.Column('last_update', sa.Date(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stock_name')
    )
    op.create_index(op.f('ix_company_stock_code'), 'company', ['stock_code'], unique=True)
    op.create_table('telegram_subscriber',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chat_id', sa.Integer(), nullable=False),
    sa.Column('joined_datetime', sa.DateTime(), nullable=False),
    sa.Column('username', sa.String(), nullable=True),
    sa.Column('first_name', sa.String(), nullable=True),
    sa.Column('last_name', sa.String(), nullable=True),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telegram_subscriber_chat_id'), 'telegram_subscriber', ['chat_id'], unique=True)
    op.create_table('announcement',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=128), nullable=True),
    sa.Column('announced_date', sa.DateTime(), nullable=False),
    sa.Column('ann_id', sa.String(length=16), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=1024), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ann_id')
    )
    op.create_table('subscribe',
    sa.Column('telegram_id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('price_alert', sa.Float(), nullable=True),
    sa.Column('price_alert_status', sa.Integer(), nullable=True),
    sa.Column('last_sent', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['telegram_id'], ['telegram_subscriber.id'], ),
    sa.PrimaryKeyConstraint('telegram_id', 'company_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('subscribe')
    op.drop_table('announcement')
    op.drop_index(op.f('ix_telegram_subscriber_chat_id'), table_name='telegram_subscriber')
    op.drop_table('telegram_subscriber')
    op.drop_index(op.f('ix_company_stock_code'), table_name='company')
    op.drop_table('company')
    # ### end Alembic commands ###
