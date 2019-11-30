from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackContext,
    Dispatcher,
)

from app.contants import MENU, ADMIN_MENU, DEFAULT_GROUP
from app.enum import Menu
from app.handlers import admin, user
from app.models import UserChat
from app.utils import MenuStringHandler


def help_(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    chat = UserChat.query.get(chat_id)
    menu = ADMIN_MENU if chat.is_admin else MENU
    update.message.reply_text(menu, parse_mode='Markdown')


def configure_dispatcher(dp: Dispatcher):

    user.add_user_handlers(dp)
    admin.add_admin_handlers(dp)

    dp.add_handler(MenuStringHandler(Menu.help, help_), group=DEFAULT_GROUP)
    dp.add_handler(CommandHandler('help', help_), group=DEFAULT_GROUP)
