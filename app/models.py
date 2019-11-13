from sqlalchemy.dialects.postgresql import JSONB

# from app.enums import ChatState
from app import db


# class UserChat(db.Model):
#     chat_id = db.Column(db.Integer, primary_key=True)
#     state = db.Column(
#         db.Enum(
#             ChatState,
#             native_enum=False,
#             create_constraint=False,
#         ),
#         nullable=False,
#     )
#     context = db.Column(JSONB, nullable=False, default={})
#
#     def to_dict(self):
#         return {
#             'chat_id': self.chat_id,
#             'state': self.state,
#             'context': self.context,
#         }
#
#     def __repr__(self):
#         return f'<UserChat {self.chat_id}>'
