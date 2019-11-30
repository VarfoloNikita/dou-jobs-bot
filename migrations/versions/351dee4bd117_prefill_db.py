""" Prefill DB


Revision ID: 351dee4bd117
Revises: 5f4fccbbe35e
Create Date: 2019-11-16 08:16:35.983782

"""
from alembic import op
import sqlalchemy as sa

from app import db
from app.models import City, Position
from csv import DictReader

# revision identifiers, used by Alembic.
revision = '351dee4bd117'
down_revision = '5f4fccbbe35e'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('COMMIT')
    with open('data/cities.csv', mode='r') as file:
        reader = DictReader(file)
        for row in reader:
            city = City(id=row['id'], name=row['name'], param=row['param'])
            db.session.add(city)
    with open('data/positions.csv', mode='r') as file:
        reader = DictReader(file)
        for row in reader:
            position = Position(id=row['id'], name=row['name'], param=row['param'])
            db.session.add(position)

    db.session.commit()


def downgrade():
    pass
