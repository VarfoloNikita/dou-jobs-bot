from typing import Callable

from sqlalchemy.orm import Query
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from app.contants import PAGINATION_SIZE
from app.models import City, Position


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
        InlineKeyboardButton('⏮️', callback_data=f'{prefix}.prev.{offset}')
        if has_prev else
        InlineKeyboardButton(' ', callback_data=f'{prefix}.prev.None'),

        # show next button only when there is not next city in list
        InlineKeyboardButton('⏭️', callback_data=f'{prefix}.next.{offset}')
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
