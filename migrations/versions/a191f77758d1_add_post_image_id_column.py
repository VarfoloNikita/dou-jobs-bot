"""Add post.image_id column

Revision ID: a191f77758d1
Revises: 0a59d3b73f1e
Create Date: 2019-11-23 20:33:08.788877

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a191f77758d1'
down_revision = '0a59d3b73f1e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('post', sa.Column('image_id', sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column('post', 'image_id')
