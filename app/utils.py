from typing import Callable, List, Optional, Union, Type

from sqlalchemy.orm import Query
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, \
    KeyboardButton, PhotoSize
from telegram.ext import Handler, MessageHandler, Filters

from app.contants import PAGINATION_SIZE
from app.enum import Menu
from app.models import City, Position, UserChat


def get_pagination_keyboard(query: Query, prefix: str, offset: int = 0) -> InlineKeyboardMarkup:
    """
    Function selects object from model with offset AND PAGINATION_SIZE and then build list of object
    with pagination  buttons, for ability to navigate between pages

    """
    items = query.limit(PAGINATION_SIZE + 1).offset(offset).all()
    keyboards = [
        [InlineKeyboardButton(item.name, callback_data=f'{prefix}.{item.id}')]
        for item in items[:PAGINATION_SIZE]
    ]

    has_next = (PAGINATION_SIZE + 1) == len(items)
    has_prev = offset > 0
    control = [
        # show previous button only if offset is more than 0
        InlineKeyboardButton('⬅️️️', callback_data=f'{prefix}.prev.{offset}')
        if has_prev else
        InlineKeyboardButton(' ', callback_data=f'{prefix}.prev.None'),

        # show next button only when there is not next city in list
        InlineKeyboardButton('➡️', callback_data=f'{prefix}.next.{offset}')
        if has_next else
        InlineKeyboardButton(' ', callback_data=f'{prefix}.next.None'),
    ]
    keyboards.append(control)
    return InlineKeyboardMarkup(keyboards, resize_keyborad=True)


def get_cities_keyboard(offset: int = 0, prefix: str = 'city') -> InlineKeyboardMarkup:
    return get_pagination_keyboard(query=City.query, prefix=prefix, offset=offset)


def get_positions_keyboard(offset: int = 0, prefix='position') -> InlineKeyboardMarkup:
    return get_pagination_keyboard(query=Position.query, prefix=prefix, offset=offset)


def update_list_page(
        update: Update,
        prefix: str,
        func: Callable[[int, str], InlineKeyboardMarkup],
) -> None:
    callback_query: CallbackQuery = update.callback_query
    *_, suffix, offset = callback_query.data.strip().split('.')

    offset: int = int(offset)
    callback_query.answer()

    if suffix == 'prev':
        new_offset = offset - PAGINATION_SIZE
        new_offset = 0 if new_offset <= 0 else new_offset
        if offset == new_offset:
            return

        markup = func(new_offset, prefix)
        callback_query.edit_message_reply_markup(markup)
        return

    if suffix == 'next':
        offset += PAGINATION_SIZE
        markup = func(offset, prefix)
        if len(markup.inline_keyboard) == 1:
            return

        callback_query.edit_message_reply_markup(markup)
        return


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_keyboard_menu(update: Update):
    message = update.message or update.callback_query.message
    chat = UserChat.query.get(message.chat_id)
    custom_keyboard = [
        [KeyboardButton(text=Menu.add.value), KeyboardButton(text=Menu.list.value)],
        [KeyboardButton(text=Menu.unsubscribe.value), KeyboardButton(text=Menu.help.value)],
    ]
    if chat.is_admin:
        custom_keyboard.extend([
            [KeyboardButton(text=Menu.stat.value), KeyboardButton(text=Menu.greeting.value)],
            [KeyboardButton(text=Menu.post.value)],
        ])
    return ReplyKeyboardMarkup(custom_keyboard)


def get_largest_photo(photos: List[PhotoSize]) -> Optional[str]:
    largest = None
    largest_size = 0
    for photo in photos:
        if photo.file_size > largest_size:
            largest = photo.file_id
            largest_size = photo.file_size

    return largest


class AnyHandler(Handler):
    def check_update(self, update):
        return True


class MenuStringHandler(MessageHandler):

    def __init__(self,
                 values: Union[Menu, Type[Menu]],
                 callback: Callable,
                 pass_update_queue=False,
                 pass_job_queue=False,
                 pass_user_data=False,
                 pass_chat_data=False,
                 message_updates=None,
                 channel_post_updates=None,
                 edited_updates=None):
        if isinstance(values, Menu):
            pattern = values.value
        else:
            pattern = '|'.join(item.value for item in values)
        super().__init__(
            Filters.regex(pattern),
            callback,
            pass_update_queue=pass_update_queue,
            pass_job_queue=pass_job_queue,
            pass_user_data=pass_user_data,
            pass_chat_data=pass_chat_data
        )
