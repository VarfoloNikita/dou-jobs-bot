""" Create user_chat table

Revision ID: ac606b47f3f4
Revises: 
Create Date: 2019-11-03 09:53:00.398732

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
from app.enums import ChatState

revision = 'ac606b47f3f4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_chat',
        sa.Column(
            'chat_id', sa.Integer(), nullable=False),
        sa.Column(
            'state',
            sa.Enum(
                ChatState,
                name='chat_state',
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column(
            'context',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('chat_id')
    )


def downgrade():
    op.drop_table('user_chat')
