import csv

import io
from typing import Dict, List, Any

from flask import make_response

from app import app, db
from app.models import UserChat, Subscription, City, Position, Stat

DataDict = Dict[str, Any]


def _make_csv(items: List[DataDict]):
    names = list(key for key in items[0])

    si = io.StringIO()
    cw = csv.DictWriter(si, names)
    cw.writeheader()
    cw.writerows(items[:1])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.route('/')
def index():
    return "<h1>Welcome to our server !!</h1>"


@app.route('/users', methods=['GET'])
def users():
    chats = UserChat.query.all()
    return _make_csv(
        items=[
            {
                'id': chat.id,
                'is_admin': chat.is_admin,
                'is_active': chat.is_active,
                'date_created': chat.date_created.date(),
            }
            for chat in chats
        ]
    )


@app.route('/subscriptions', methods=['GET'])
def subscriptions():
    items = db.session.query(Subscription, City, Position).join(City).join(Position).all()
    return _make_csv(
        items=[
            {
                'id': subscription.id,
                'chat_id': subscription.chat_id,
                'city': city.name,
                'category': position.name,
                'date_created': subscription.date_created.date(),
            }
            for subscription, city, position in items
        ]
    )


@app.route('/actions', methods=['GET'])
def actions():
    items = Stat.query.all()
    return _make_csv(
        items=[
            {
                'action': stat.action,
                'chat_id': stat.chat_id,
                'date': stat.date.date(),
            }
            for stat in items
        ]
    )

