from enum import Enum

from telegram import Update
from telegram.ext import (
    MessageHandler,
    Filters,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
)

from app import updater


class AddSubscriptionStates(Enum):
    city = 'city'
    position = 'position'


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Привіт я телеграм бот який буде шукати роботу за '
        'тебе. \n'
        'Ось список  ',
    )


def menu(update: Update, context: CallbackContext):
    update.message.reply(
        'Привіт я телеграм бот який буде шукати роботу за '
        'тебе. \n'
        'Ось список  ',
    )


def add_subscription(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Введіть місто"
    )
    return AddSubscriptionStates.city


def add_subscription_fallback(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Conversation fallback"
    )
    return ConversationHandler.END


def add_subscription_city(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Місто додано, тепер додайте позицію"
    )
    return AddSubscriptionStates.position


def add_subscription_position(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Позицію додано, тепер додайте позицію"
    )
    return ConversationHandler.END


def list_subscription(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Ось список твоїх підписок"
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
                MessageHandler(Filters.text, add_subscription_city),
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

dp.add_handler(MessageHandler(Filters.text, fallback))
