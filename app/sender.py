import logging

from app import db, app, bot
from app.models import Subscription, Vacancy, VacancyParameters, UserChat, VacancyChat, utc_now


def send_vacancy_to_chat(chat: UserChat, vacancy: Vacancy):
    bot.send_message(
        chat_id=chat.id,
        text=vacancy.text,
        parse_mode='Markdown',
    )


def process_vacancy(vacancy: Vacancy):
    app.logger.info(f'Process vacancy {vacancy.title}')

    for parameter in vacancy.get_not_processed_parameters():
        process_parameters(parameter, vacancy)

    vacancy.date_sent = utc_now()
    db.session.commit()


def process_parameters(parameter: VacancyParameters, vacancy: Vacancy):
    app.logger.info(f'Process vacancy_parameters {parameter.id}')

    for subscription in parameter.subscriptions:
        process_subscription(subscription, vacancy)

    parameter.date_processed = utc_now()
    db.session.commit()


def process_subscription(subscription: Subscription, vacancy: Vacancy):
    chat = VacancyChat(chat_id=subscription.chat_id, vacancy=vacancy.id)
    if chat.exsits():
        return

    db.session.add(chat)
    db.session.commit()


def send_vacancies():
    # get unsent vacancies
    vacancies = db.session.query(Vacancy).filter(Vacancy.date_sent.is_(None)).all()

    for vacancy in vacancies:
        process_vacancy(vacancy)
