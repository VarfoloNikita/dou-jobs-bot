import functools
from typing import Callable, Any

from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Dispatcher,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    CallbackContext,
)

from app import db, bot, app
from app.contants import DEFAULT_GREETING, HOST, DEFAULT_GROUP
from app.models import Greeting, Post, City, Position, Subscription, utc_now, UserChat
from app.utils import update_list_page, get_cities_keyboard, get_positions_keyboard, AnyHandler, get_largest_photo

HandlerFunction = Callable[[Update, CallbackContext], Any]

SET_GREETING = 'greeting'
CREATE_JOB = 'create_job'
SEND_PHOTO = 'send_photo'


def _empty_callback(update: Update, context: CallbackContext):
    update.callback_query.answer()


def admin_required(handler: HandlerFunction) -> HandlerFunction:
    """ Decorator for protecting admin handlers from unnecessary access """

    @functools.wraps(handler)
    def wrapper(update: Update, context: CallbackContext):
        message: Message = update.message or update.callback_query.message
        chat_id = message.chat_id
        chat = UserChat.query.get(chat_id)
        if not chat.is_admin:
            app.logger.info('Access denied to admin handler')
            return

        return handler(update, context)

    return wrapper


def send_post(post: Post):
    query = db.session.query(Subscription).distinct(Subscription.chat_id)
    if post.city_id is not None:
        query = query.filter(Subscription.city_id == post.city_id)
    if post.position_id is not None:
        query = query.filter(Subscription.position_id == post.position_id)

    items = query.all()
    for subscription in items:
        if post.image_id:
            bot.send_photo(
                chat_id=subscription.chat_id,
                photo=post.image_id,
                caption=post.text,
                parse_mode="Markdown",
                disable_web_page_preview=False,
            )

        else:
            bot.send_message(
                chat_id=subscription.chat_id,
                text=post.text,
                parse_mode='Markdown',
                disable_web_page_preview=False,
            )

    post.date_sent = utc_now()
    db.session.commit()

    return items


def _get_post_id(update: Update):
    callback_query: CallbackQuery = update.callback_query
    callback_query.answer()
    _, post_id, *_ = callback_query.data.strip().split('.')
    return post_id


@admin_required
def get_greeting(update: Update, context: CallbackContext):
    greeting = Greeting.query.get(1)
    text = greeting.text if greeting else DEFAULT_GREETING
    update.message.reply_text(
        "Напишіть знизу тест, яким я буду вітатися з новими користувачами. "
        "Якщо не хочете нічого змінювати введіть команду /cancel\n\n"
        "_Зараз я вітаюся таким повідомленням_:\n"
        f"{text}",
        parse_mode="Markdown"
    )
    return SET_GREETING


def update_greeting(update: Update, context: CallbackContext):
    message: Message = update.message
    Greeting.set_text(text=message.text)
    update.message.reply_text(
        "Вітання змінено! Якщо захочете змінити чи відредагувати вітання "
        "повторіть команду /greeting",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


def greeting_fallback(update: Update, context: CallbackContext):
    update.message.reply_text(
        text="Введіть, будь ласка, текст для привітання",
        parse_mode="Markdown",
    )


def cancel_update_greeting(update: Update, context: CallbackContext):
    update.message.reply_text(
        text=(
            "Ви залишили старе привітання, якщо захочете змінити "
            "привітання знову введіть команду /greeting знову"
        ),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


@admin_required
def get_statistic(update: Update, context: CallbackContext):

    update.message.reply_text(
        text=(
            f"Посилання з даними:\n\n"
            f"Користувачі: {HOST}/users \n"
            f"Дії: {HOST}/actions \n"
            f"Підписки: {HOST}/subscriptions \n"
        ),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


@admin_required
def create_job(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Введіть нижче текст повідомлення який ви хочете розіслати користувачам. "
        "Я не надсилатиму сповіщення відразу ж, лише тоді коли ви натиснете "
        "кнопку 'Опублікувати'. Для повідомлення використовується Markdown. \n"
        "Щоб дабавити зображення під текстом, вставте посилання на це зображення в "
        "такому форматі: [[.]](https://picsum.photos/id/501/536/354)",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    return CREATE_JOB


def post_fallback(update: Update, context: CallbackContext):
    message: Message = update.message or update.callback_query.message
    message.reply_text("Введіть, будь ласка, текст. Зображення ви можете прикріпити пізніше.")


def save_post(update: Update, context: CallbackContext):

    message: Message = update.message
    job_text: str = message.text or message.caption or ''

    photo_id = get_largest_photo(message.photo)

    # Insert raw post to database
    post = Post(text=job_text, image_id=photo_id)
    db.session.add(post)
    db.session.commit()

    _send_job_post(post, update)

    return ConversationHandler.END


def _send_job_post(post: Post, update: Update):
    # build reply text
    buttons = []

    city = City.query.get(post.city_id) if post.city_id is not None else None
    position = Position.query.get(post.position_id) if post.position_id is not None else None

    city_text = f'Змінити місто ({city.name})' if city else 'Додати місто 🏙️'
    button = InlineKeyboardButton(text=city_text, callback_data=f'post.{post.id}.city.page')
    buttons.append([button])

    position_text = f'Змінити категорію ({position.name})' if position else 'Додати категорію 🤖'
    button = InlineKeyboardButton(text=position_text, callback_data=f'post.{post.id}.position.page')
    buttons.append([button])

    button = InlineKeyboardButton(text='Опублікувати 📨️', callback_data=f'post.{post.id}.publish')
    buttons.append([button])

    button = InlineKeyboardButton(text='Видалити ❌', callback_data=f'post.{post.id}.delete')
    buttons.append([button])

    message_text = post.text

    if post.is_sent:
        values = '/'.join(i.name for i in [city, position] if i)
        text = 'Відправлено 🎉 {}'.format(f'({values})' if values else '')
        button = InlineKeyboardButton(text=text, callback_data=f'post.{post.id}.none')
        buttons = [[button]]

    markup = InlineKeyboardMarkup(buttons, resize_keyboard=True)
    message: Message = update.message or update.callback_query.message
    if update.callback_query:
        if post.image_id:
            message.edit_caption(
                caption=message_text,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        else:
            message.edit_text(
                text=message_text,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        return

    if post.image_id is not None:
        message.reply_photo(
            photo=post.image_id,
            caption=message_text,
            parse_mode="Markdown",
            reply_markup=markup,
        )
    else:
        message.reply_text(
            text=message_text,
            parse_mode="Markdown",
            reply_markup=markup,
        )


def city_page(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    post = Post.query.get(post_id)

    text = (
        "Вкажіть місто публікації вакансії, для цього оберіть один і "
        "з варіантів зі списку нижче. Використовуйте кнопки ⬅️️ та ➡️ для "
        "навігації між сторінками списку"
    )
    reply_markup = get_cities_keyboard(prefix=f'post.{post_id}.city')

    if post.image_id:
        update.callback_query.message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        update.callback_query.message.edit_text(text=text, reply_markup=reply_markup)


def city_navigate(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    return update_list_page(update, prefix=f'post.{post_id}.city', func=get_cities_keyboard)


def city_choose(update: Update, context: CallbackContext):
    callback_query: CallbackQuery = update.callback_query
    callback_query.answer()
    _, post_id, _, city_id = callback_query.data.strip().split('.')

    # Save changes
    post = Post.query.get(post_id)
    post.city_id = city_id
    db.session.commit()

    _send_job_post(post, update)


def position_page(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    post = Post.query.get(post_id)

    text = (
        "Оберіть одну з категорій для насилання вакансії, для цього оберіть "
        "один із варіантів зі списку нижче. Використовуйте кнопки ⬅️️ та ➡️ для "
        "навігації між сторінками списку."
    )
    reply_markup = get_positions_keyboard(prefix=f'post.{post_id}.position')

    if post.image_id:
        update.callback_query.message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        update.callback_query.message.edit_text(text=text, reply_markup=reply_markup)


def position_navigate(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    return update_list_page(update, prefix=f'post.{post_id}.position', func=get_positions_keyboard)


def position_choose(update: Update, context: CallbackContext):
    callback_query: CallbackQuery = update.callback_query
    callback_query.answer()
    _, post_id, _, position_id = callback_query.data.strip().split('.')

    # Save changes
    post = Post.query.get(post_id)
    post.position_id = position_id
    db.session.commit()

    _send_job_post(post, update)


def delete_post(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    post = Post.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    update.callback_query.message.delete()


def publish_post(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    post = Post.query.get(post_id)

    text = 'Відправляємо повідомлення ⌛'
    if post.image_id:
        update.callback_query.message.edit_caption(caption=text)
    else:
        update.callback_query.edit_message_text(text)

    send_post(post)

    _send_job_post(post, update)


def cancel_create_post(update: Update, context: CallbackContext):
    update.message.reply_text("Гаразд, ви відхили створення повідомлення")
    return ConversationHandler.END


def print_bad_query(update: Update, context: CallbackContext):
    update.callback_query.answer()


def add_admin_handlers(dp: Dispatcher):
    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('greeting', get_greeting)],
            states={
                SET_GREETING: [MessageHandler(Filters.text, update_greeting)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_update_greeting),
                MessageHandler(Filters.command, cancel_update_greeting),
                AnyHandler(greeting_fallback),
            ],
            allow_reentry=True,
        ),
        group=1,
    )
    dp.add_handler(CommandHandler('stat', get_statistic), group=DEFAULT_GROUP)

    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('post', create_job)],
            states={
                CREATE_JOB: [
                    MessageHandler(Filters.text | Filters.photo, save_post),
                ],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_create_post),
                MessageHandler(Filters.command, cancel_create_post),
                AnyHandler(post_fallback)
            ],
            allow_reentry=True,
        ),
        group=2,
    )
    dp.add_handler(CallbackQueryHandler(city_page, pattern=r'post\.\d+\.city\.page'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(city_navigate, pattern=r'post\.\d+\.city\.(prev|next)\.\d+'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(city_choose, pattern=r'post\.\d+\.city\.\d+'), group=DEFAULT_GROUP)

    dp.add_handler(CallbackQueryHandler(position_page, pattern=r'post\.\d+\.position\.page'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(position_navigate, pattern=r'post\.\d+\.position\.(prev|next)\.\d+'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(position_choose, pattern=r'post\.\d+\.position\.\d+'), group=DEFAULT_GROUP)

    dp.add_handler(CallbackQueryHandler(delete_post, pattern=r'post\.\d+\.delete'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(publish_post, pattern=r'post\.\d+\.publish'), group=DEFAULT_GROUP)
    dp.add_handler(CallbackQueryHandler(_empty_callback, pattern=r'post\.\d+\.none'), group=DEFAULT_GROUP)

