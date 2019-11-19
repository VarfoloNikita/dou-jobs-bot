import sqlalchemy as sa

from app import db, app, bot
from app.models import Subscription, Vacancy, VacancyParameters, VacancyChat, utc_now
from app.utils import chunks


def send_vacancy_to_chat(chat: VacancyChat, vacancy: Vacancy):
    bot.send_message(
        chat_id=chat.chat_id,
        text=vacancy.text,
        parse_mode='Markdown',
    )


def dispatch_vacancies():
    # get unsent vacancies
    vacancies = (
        db.session.query(Vacancy, Subscription)
        .join(VacancyParameters, Vacancy.id == VacancyParameters.vacancy_id)
        .join(
            Subscription,
            sa.and_(
                Subscription.city_id == VacancyParameters.city_id,
                Subscription.position_id == VacancyParameters.position_id,
            ),
        )
        .outerjoin(
            VacancyChat,
            sa.and_(
                VacancyChat.chat_id == Subscription.chat_id,
                VacancyChat.vacancy_id == Vacancy.id
            )
        )
        .filter(VacancyChat.id.is_(None))
        .all()
    )
    for chunk in chunks(vacancies, n=10):
        for vacancy, subscription in chunk:
            chat = VacancyChat(
                chat_id=subscription.chat_id,
                vacancy_id=vacancy.id,
                attempt=0,
            )
            chat = chat.find()
            db.session.add(chat)
            db.session.commit()


def send_vacancies():
    vacancies = (
        db.session.query(VacancyChat, Vacancy).join(Vacancy)
        .filter(
            VacancyChat.date_sent.is_(None),
            VacancyChat.attempt < 10000,
        )
    )
    for chat, vacancy in vacancies:
        try:
            send_vacancy_to_chat(chat, vacancy)
            chat.date_sent = utc_now()
        except Exception as exception:
            chat.attempt += 1
            print(vacancy.text)
            app.logger.exception(
                msg='Error on sending vacancy',
                exc_info=exception,
            )

        db.session.commit()


