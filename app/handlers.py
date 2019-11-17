from telegram import Update
from telegram.ext import (
    MessageHandler,
    Filters,
    CommandHandler,
    CallbackContext,
    Dispatcher,
)

from app.admin import add_admin_handlers
from app.contants import MENU, ADMIN_MENU, DEFAULT_GREETING
from app.models import UserChat, Greeting
from app.subscription import add_subscription_handlers


def start(update: Update, context: CallbackContext):

    # create and get new user chat instance
    chat = UserChat(
        id=update.message.chat_id,
        is_admin=False,
        is_active=True,
    )
    chat = chat.soft_add()

    # select greeting and menu items
    menu = ADMIN_MENU if chat.is_admin else MENU
    greeting = 'Вітаю, мій володаре 👑'
    if not chat.is_admin:
        item = Greeting.query.first()
        greeting = item.text if item else DEFAULT_GREETING

    # greet with user
    update.message.reply_text(f'{greeting}.\n{menu}', parse_mode='Markdown')


def help_(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    chat = UserChat.query.get(chat_id)
    menu = ADMIN_MENU if chat.is_admin else MENU
    update.message.reply_text(menu, parse_mode='Markdown')


def fallback(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Я тебе не розумію.")


def configure_dispatcher(dp: Dispatcher):
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_))

    add_subscription_handlers(dp)
    add_admin_handlers(dp)

    dp.add_handler(MessageHandler(Filters.text, fallback))
