"""empty message

Revision ID: 502c6969c42f
Revises: 351dee4bd117
Create Date: 2019-11-19 19:44:28.897603

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '502c6969c42f'
down_revision = '351dee4bd117'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vacancy', sa.Column('date_processed', sa.DateTime(), nullable=True))
    op.drop_column('vacancy', 'date_sent')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('vacancy', sa.Column('date_sent', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_column('vacancy', 'date_processed')