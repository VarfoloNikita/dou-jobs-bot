from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    MessageHandler,
    Filters,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
)

from app import updater

CITIES = [
    ('Київ', 1),
    ('Полтава', 2),
    ('Одеса', 3),
    ('Львів', 4),
    ('Вінния', 5),
    ('Харків', 6),
    ('Донецьк', 7),
]


MENU = """
*Список підтримуваних команд:*
 - /start - почати роботу з ботом
 - /list - список підписок
 - /add - підписатися на нові сповіщення
 - /help - отримати довідку
"""


class AddSubscriptionStates(Enum):
    city = 'city'
    position = 'position'


def __send_help(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Спиос'
    )


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Привіт я телеграм бот який буде шукати роботу за тебе.'
        '\n'
        '{}'.format(MENU),
        parse_mode='Markdown',
    )


def help_(update: Update, context: CallbackContext):
    update.message.reply_text(MENU, parse_mode='Markdown')


def add_subscription(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Для підпсання на нові вакансії потрібно пройти невелике опитування. "
        "Якщо бажаєте відхили опитування введіть команду /cancel"
    )

    keyboards = [
        [InlineKeyboardButton(name, callback_data=f'city.{id_}')]
        for name, id_ in CITIES
    ]
    keyboards.append([
        InlineKeyboardButton('<', callback_data='city.prev'),
        InlineKeyboardButton('>', callback_data='city.next'),
    ])
    update.message.reply_text(
        "Вкажіть місто де потрібно шукати вакансії",
        reply_markup=InlineKeyboardMarkup(keyboards)
    )
    return AddSubscriptionStates.city


def add_subscription_city(update: Update, context: CallbackContext):
    data: str = update.callback_query.data
    _, suffix = data.strip().split('.')

    update.message.reply_text(
       f"Місто {suffix} додано, тепер додайте позицію"
    )
    return AddSubscriptionStates.position


def add_subscription_city_navigate(update: Update, context: CallbackContext):
    data: str = update.callback_query.data
    _, suffix = data.strip().split('.')
    if suffix == 'prev':
        pass
        return
    if suffix == 'next':
        pass
        return


def add_subscription_fallback(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Conversation fallback"
    )
    return ConversationHandler.END


def add_subscription_position(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Супер, тепер я буду сповіщати тебе про нові вакансії"
    )
    return ConversationHandler.END


def list_subscription(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Список підписок"
    )


def fallback(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Я тебе не розумію."
    )


dp = updater.dispatcher
dp.add_handler(CommandHandler('start', start))

dp.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler('add', add_subscription)],
        states={
            AddSubscriptionStates.city: [
                CallbackQueryHandler(add_subscription_city_navigate, pattern=r'city\.(prev|next)'),
                CallbackQueryHandler(add_subscription_city, pattern=r'city\.\d+')
            ],
            AddSubscriptionStates.position: [
                MessageHandler(Filters.text, add_subscription_position),
            ],
        },
        fallbacks=[
            MessageHandler(Filters.text, add_subscription_fallback),
        ],
    )
)
dp.add_handler(CommandHandler('list', list_subscription))
dp.add_handler(CommandHandler('help', help_))

dp.add_handler(MessageHandler(Filters.text, fallback))
