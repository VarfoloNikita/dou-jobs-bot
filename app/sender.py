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

    success = True
    for parameter in vacancy.parameters:
        success *= process_parameters(parameter, vacancy)

    if success:
        vacancy.date_sent = utc_now()
        db.session.commit()

    return success


def process_parameters(parameter: VacancyParameters, vacancy: Vacancy) -> bool:
    app.logger.info(f'Process vacancy_parameters {parameter.id}')

    success = True
    for subscription in parameter.subscriptions:
        success *= process_subscription(subscription, vacancy)

    if success:
        parameter.date_sent = utc_now()
        db.session.commit()

    return success


def process_subscription(subscription: Subscription, vacancy: Vacancy):
    user_chat = subscription.chat
    chat = VacancyChat(
        chat_id=user_chat.id,
        vacancy_id=vacancy.id,
        attempt=1,
    )
    chat = chat.get()

    if chat.attempt > 500 or chat.date_sent is not None:
        return True

    db.session.add(chat)
    try:
        send_vacancy_to_chat(user_chat, vacancy)
        chat.date_sent = utc_now()
        app.logger.info(f'New vacancy was sent: {chat.id} {vacancy.title}')
    except Exception as exception:
        chat.attempt += 1
        db.session.commit()
        app.logger.exception(
            msg='Message failed',
            exc_info=exception,
        )
        return False

    db.session.commit()
    return True


def send_vacancies():
    # get unsent vacancies
    vacancies = db.session.query(Vacancy).filter(Vacancy.date_sent.is_(None)).all()

    for vacancy in vacancies:
        process_vacancy(vacancy)
