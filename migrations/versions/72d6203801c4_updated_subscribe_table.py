"""updated subscribe table

Revision ID: 72d6203801c4
Revises: d422004e26a5
Create Date: 2020-03-06 23:51:09.406152

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72d6203801c4'
down_revision = 'd422004e26a5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('telegram_subscriber',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chat_id', sa.Integer(), nullable=False),
    sa.Column('joined_datetime', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telegram_subscriber_chat_id'), 'telegram_subscriber', ['chat_id'], unique=True)
    op.drop_index('ix_telegramsubscriber_chat_id', table_name='telegramsubscriber')
    print("Dropped index")
    op.drop_constraint(None, 'subscribe', type_='foreignkey')
    print("Dropped constraint")
    op.drop_table('telegramsubscriber')
    print("Dropped table")
    op.create_foreign_key(None, 'subscribe', 'telegram_subscriber', ['telegram_id'], ['id'])
    print("Created new foreign key")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'subscribe', type_='foreignkey')
    op.create_foreign_key(None, 'subscribe', 'telegramsubscriber', ['telegram_id'], ['id'])
    op.create_table('telegramsubscriber',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('chat_id', sa.INTEGER(), nullable=False),
    sa.Column('joined_datetime', sa.DATETIME(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_telegramsubscriber_chat_id', 'telegramsubscriber', ['chat_id'], unique=1)
    op.drop_index(op.f('ix_telegram_subscriber_chat_id'), table_name='telegram_subscriber')
    op.drop_table('telegram_subscriber')
    # ### end Alembic commands ###
