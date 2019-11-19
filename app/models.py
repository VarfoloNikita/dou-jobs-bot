import datetime
import sqlalchemy as sa
from sqlalchemy import orm
from app import db
from app.enum import Action

utc_now = datetime.datetime.utcnow


class UserChat(db.Model):
    __tablename__ = 'user_chat'

    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    context = db.Column(db.JSON, nullable=False, default=lambda: {})
    date_created = db.Column(db.DateTime, default=utc_now)

    subscriptions = db.relationship('Subscription', backref='chat', lazy=True)

    def soft_add(self) -> 'UserChat':
        chat = UserChat.query.get(self.id)
        if not chat:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)
            return self
        return chat


class Subscription(db.Model):

    __table_args__ = (
        db.UniqueConstraint('chat_id', 'city_id', 'position_id', name='unique_user_subscription'),
    )

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('user_chat.id'), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=utc_now)

    def soft_add(self) -> None:
        subscription = Subscription.query.filter_by(
            chat_id=self.chat_id,
            city_id=self.city_id,
            position_id=self.position_id,
        ).first()
        if not subscription:
            db.session.add(self)


class Position(db.Model):
    __table_args__ = (db.UniqueConstraint('name', name='unique_position_name'),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    param = db.Column(db.String(256))

    def __repr__(self):
        return f'<City id={self.id} name={self.name}'


class City(db.Model):

    __table_args__ = (db.UniqueConstraint('name', name='unique_city_name'),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    param = db.Column(db.String(256))

    def __repr__(self):
        return f'<City id={self.id} name={self.name}'


class Greeting(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    text = db.Column(db.Text)

    @staticmethod
    def set_text(text):
        greeting = Greeting.query.get(1)
        if not greeting:
            greeting = Greeting(text=text)
            db.session.add(greeting)

        greeting.text = text
        db.session.commit()


class Statistic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(
        db.Enum(
            Action,
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
    )
    date = db.Column(db.DateTime, default=utc_now)
    chat_id = db.Column(db.Integer, db.ForeignKey('user_chat.id'), nullable=False)
    meta = db.Column(db.JSON, nullable=False, default=lambda: {})


class Post(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    position_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=True)
    date_sent = db.Column(db.DateTime, nullable=True)

    @property
    def is_sent(self):
        return self.date_sent is not None


class Vacancy(db.Model):
    """ Table for storing vacancies metadata """

    __table_args__ = (db.UniqueConstraint('url', name='unique_vacancy'),)

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=utc_now)
    date_processed = db.Column(db.DateTime, nullable=True)

    def get_not_processed_parameters(self):
        return (
            VacancyParameters.query
            .filter(
                VacancyParameters.vacancy_id == self.id,
                VacancyParameters.date_processed.is_(None),
            )
            .all()
        )

    def soft_add(self) -> 'Vacancy':
        chat = Vacancy.query.filter(Vacancy.url == self.url).first()
        if not chat:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)
            return self
        return chat

    def __repr__(self):
        return f'<Vacancy title={self.title[:50]} text={self.title[:50]}>'


class VacancyParameters(db.Model):
    """ Table for storing cities and positions related to vacancy """

    __table_args__ = (
        db.UniqueConstraint(
            'city_id', 'position_id', 'vacancy_id',
            name='unique_vacancy_parameters',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=False)
    vacancy_id = db.Column(db.Integer, db.ForeignKey('vacancy.id'), nullable=False)

    date_created = db.Column(db.DateTime, nullable=False, default=utc_now)
    date_sent = db.Column(db.DateTime, nullable=True)

    subscriptions = db.relationship(
        'Subscription',
        primaryjoin=sa.and_(
            city_id == orm.foreign(Subscription.city_id),
            position_id == orm.foreign(Subscription.position_id),
        ),
        lazy=True,
    )

    def exists(self) -> bool:
        vacancy = VacancyParameters.query.filter(
            VacancyParameters.city_id == self.city_id,
            VacancyParameters.position_id == self.position_id,
            VacancyParameters.vacancy_id == self.vacancy_id,
        ).first()
        return bool(vacancy)


class VacancyChat(db.Model):
    """ Table for storing sent/unsent vacancies for given chat """

    __table_args__ = (
        db.UniqueConstraint(
            'chat_id', 'vacancy_id',
            name='unique_vacancy_chat',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('user_chat.id'), nullable=False)
    vacancy_id = db.Column(db.Integer, db.ForeignKey('vacancy.id'), nullable=False)
    attempt = db.Column(db.Integer, nullable=False, default=1)
    date_created = db.Column(db.DateTime, nullable=False, default=utc_now)
    date_sent = db.Column(db.DateTime, nullable=True)

    def exists(self):
        query = VacancyChat.query.filter_by(chat_id=self.chat_id, vacancy_id=self.vacancy_id)
        return bool(query.first())




