from telegram import Update, CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    MessageHandler,
    Filters,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    Dispatcher,
    PrefixHandler
)

from app import db, parser, sender, updater
from app.contants import DEFAULT_GREETING, ADMIN_MENU, MENU, DEFAULT_GROUP
from app.enum import AddSubscriptionStates, SubscriptionPageState, Action, Menu
from app.models import City, Position, Subscription, UserChat, Greeting, Stat
from app.utils import get_cities_keyboard, update_list_page, get_positions_keyboard, AnyHandler, get_keyboard_menu, \
    MenuStringHandler


def start(update: Update, context: CallbackContext):
    # create and get new user chat instance
    chat = UserChat(
        id=update.message.chat_id,
        is_admin=False,
        is_active=True,
    )
    chat = chat.soft_add()

    # select greeting and menu item
    item = Greeting.query.first()
    greeting = item.text if item else DEFAULT_GREETING

    greeting += f"\n\n{MENU if chat.is_admin else ADMIN_MENU}"

    # greet with user
    update.message.reply_text(
        text=greeting,
        parse_mode='Markdown',
    )
    return add_subscription(update, context)


def add_subscription(update: Update, context: CallbackContext):
    update.message.reply_text(
        text=(
            "Вкажіть місто де потрібно шукати вакансії, для цього оберіть один "
            "і з варіантів зі списку нижче. Використовуйте кнопки ⬅️️ та ➡️ для навігації між "
            "сторінками списку. Якщо захочете віхилити опитування, натисніть /cancel"
        ),
        reply_markup=get_cities_keyboard(),
    )
    return AddSubscriptionStates.city


def add_city_navigate(update: Update, context: CallbackContext):
    return update_list_page(update, prefix='city', func=get_cities_keyboard)


def add_city(update: Update, context: CallbackContext):
    callback_query: CallbackQuery = update.callback_query
    _, suffix = callback_query.data.strip().split('.')
    city = City.query.filter_by(id=suffix).first()

    callback_query.answer(
        callback_query=callback_query.id,
        text=f"Дякую, я запам'ятав твій вибір",
        cache_time=60,
    )
    message: Message = callback_query.message
    message.reply_text(
        text=(
            f"Ви обрали місто {city.name}. Залишилося додати категорію "
            f"в якій потрібно шукати вакансії. Оберіть один і з варіантів "
            f"перелічених нижче 👇🏼"
        ),
        reply_markup=get_positions_keyboard(),
    )
    context.user_data['city_id'] = city.id
    context.user_data['city_name'] = city.name

    return AddSubscriptionStates.position


def add_position_navigate(update: Update, context: CallbackContext):
    return update_list_page(update, prefix='position', func=get_positions_keyboard)


def add_subscription_fallback(update: Update, context: CallbackContext):
    update.message.reply_text(
        text=(
            "Ви ще незавершили додавання нової підписки. Оберіть варіант зі списку "
            "вище або введіть команду /cancel, щоб відхили додавання підписки."
        ),
    )


def add_position(update: Update, context: CallbackContext):
    callback_query: CallbackQuery = update.callback_query
    _, suffix = callback_query.data.strip().split('.')
    position = Position.query.filter_by(id=suffix).first()
    city_id: str = context.user_data['city_id']
    city = City.query.get(city_id)
    message: Message = callback_query.message

    subscription = Subscription(
        chat_id=message.chat_id,
        city_id=city_id,
        position_id=position.id,
    )
    subscription.soft_add()
    db.session.commit()

    callback_query.answer(
        callback_query=callback_query.id,
        text=f"Дякую, я запам'ятав твій вибір",
        cache_time=60,
    )

    message.reply_text(
        text=(
            f"Опитування завершено 🎉. \n"
            f"Тепер я буду тебе повіщувати про "
            f"нові вакансії з категорії *{position.name}* у місті *{city.name}*."
            f"\n\n"
            f"Також зараз я пошукаю вакансії і ж за декілька хвилин я надішлю тобі список "
            f"вакансій за вашими параметрами."
        ),
        parse_mode='Markdown',
        reply_markup=get_keyboard_menu(update),
    )
    stat = Stat(chat_id=message.chat_id, action=Action.subscribed.value)
    db.session.add(stat)
    db.session.commit()

    vacancies = parser.update_new_vacancies(city, position)
    if not vacancies:
        message.reply_text(
            text=f"🤷‍♀️ На жаль, у місті *{city.name}* немає вакансій в категорії *{position.name}*",
            parse_mode='Markdown',
        )
    # send only 10 vacancies for preventing spamming
    vacancies = vacancies[:10]
    sender.send_vacancies(vacancies, message.chat_id)

    return ConversationHandler.END


def cancel_add_subscription(update: Update, context: CallbackContext):
    update.message.reply_text(
        text='Гаразд додамо підписку іншого разу',
        reply_markup=get_keyboard_menu(update),
    )
    return ConversationHandler.END


def list_subscription(update: Update, context: CallbackContext):
    message: Message = update.message or update.callback_query.message
    send_function = (
        message.reply_text
        if update.message else
        update.callback_query.edit_message_text
    )
    chat_id = message.chat_id
    items = (
        db.session.query(Subscription, Position, City).join(Position).join(City)
        .filter(Subscription.chat_id == chat_id).all()
    )

    if not items:
        send_function(text=(
            "У вас немає підписок, щоб піписатися на нові вакансії "
            "виконайте команду /add"
        ))
        return

    keyboards = []
    for subscription, position, city in items:
        button_text = f'{position.name} в місті {city.name}    ➡️'
        callback_data = f'subscription.choose.{subscription.id}'
        button = InlineKeyboardButton(button_text, callback_data=callback_data)
        keyboards.append([button])

    markup = InlineKeyboardMarkup(keyboards)
    send_function(
        text="Ось список твої підписок",
        reply_markup=markup,
    )

    return SubscriptionPageState.list


def choose_subscription(update: Update, context: CallbackContext):
    callback_query: CallbackQuery = update.callback_query
    _, _, suffix = callback_query.data.strip().split('.')
    subscription, position, city = (
        db.session.query(Subscription, Position, City).join(Position).join(City)
            .filter(Subscription.id == suffix).first()
    )
    keyboards = [
        [
            InlineKeyboardButton(
                text='↩️ Назад',
                callback_data='subscription.list',
            ),
            InlineKeyboardButton(
                text='❌ Видалати',
                callback_data=f'subscription.delete.{subscription.id}',
            ),
        ]
    ]

    markup = InlineKeyboardMarkup(keyboards, resize_keyboard=True)

    callback_query.answer()
    callback_query.edit_message_text(
        text=(
            "Ваша підписка: \n"
            f"*Місто:* {city.name}\n"
            f"*Категорія:* {position.name}"
        ),
        parse_mode="Markdown",
        reply_markup=markup,
    )


def delete_subscription(update: Update, context: CallbackContext):
    callback_query: CallbackQuery = update.callback_query
    _, _, suffix = callback_query.data.strip().split('.')

    subscription = Subscription.query.get(suffix)
    if not subscription:
        return

    chat_id = subscription.chat_id

    db.session.delete(subscription)
    db.session.commit()

    if not Subscription.query.first():
        stat = Stat(chat_id=chat_id, action=Action.unsubscribe.value)
        db.session.add(stat)
        db.session.commit()

    list_subscription(update, context)


def unsubscribe_all(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    subscriptions = db.session.query(Subscription).filter_by(chat_id=chat_id)
    subscriptions.delete(synchronize_session='fetch')

    stat = Stat(chat_id=chat_id, action=Action.unsubscribe.value)
    db.session.add(stat)
    db.session.commit()

    update.message.reply_text("Ви відписалися від всіх розсилок вакансій")


def cancel_add_subscription_command(update: Update, context: CallbackContext):
    result = cancel_add_subscription(update, context)
    updater.dispatcher.process_update(update)
    return result


def add_user_handlers(dp: Dispatcher):
    dp.add_handler(
        ConversationHandler(
            entry_points=[
                MenuStringHandler(Menu.add, add_subscription),
                CommandHandler('add', add_subscription),
                CommandHandler('start', start),
            ],
            states={
                AddSubscriptionStates.city: [
                    CallbackQueryHandler(add_city_navigate, pattern=r'city\.(prev|next)\.\d+'),
                    CallbackQueryHandler(add_city, pattern=r'city\.\d+')
                ],
                AddSubscriptionStates.position: [
                    CallbackQueryHandler(add_position_navigate, pattern=r'position\.(prev|next)\.\d+'),
                    CallbackQueryHandler(add_position, pattern=r'position\.\d+')
                ],
            },
            fallbacks=[
                MenuStringHandler(Menu, cancel_add_subscription),
                CommandHandler('cancel', cancel_add_subscription),
                MessageHandler(Filters.command, cancel_add_subscription),
                AnyHandler(add_subscription_fallback),
            ],
            allow_reentry=True,
        ),
        group=0,
    )

    # Manage subscription
    dp.add_handler(MenuStringHandler(Menu.list, list_subscription), group=DEFAULT_GROUP)
    dp.add_handler(CommandHandler('list', list_subscription), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(choose_subscription, pattern=r'subscription\.choose\.\d+'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(delete_subscription, pattern=r'subscription\.delete\.\d+'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(list_subscription, pattern=r'subscription\.list'), group=DEFAULT_GROUP)

    dp.add_handler(MenuStringHandler(Menu.unsubscribe, unsubscribe_all), group=DEFAULT_GROUP)
    dp.add_handler(CommandHandler('unsubscribe', unsubscribe_all), group=DEFAULT_GROUP)
