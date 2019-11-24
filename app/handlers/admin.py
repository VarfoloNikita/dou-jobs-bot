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
from app.contants import DEFAULT_GREETING, HOST
from app.models import Greeting, Post, City, Position, Subscription, utc_now, UserChat
from app.utils import update_list_page, get_cities_keyboard, get_positions_keyboard, AnyHandler

HandlerFunction = Callable[[Update, CallbackContext], Any]

SET_GREETING = 'greeting'
CREATE_JOB = 'create_job'
SEND_PHOTO = 'send_photo'


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
        bot.send_message(
            chat_id=subscription.chat_id,
            text=post.text,
            parse_mode='Markdown',
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
        "такому форматі: [[ ]](https://picsum.photos/id/501/536/354)",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    return CREATE_JOB


def post_fallback(update: Update, context: CallbackContext):
    message: Message = update.message or update.callback_query.message
    message.reply_text("Введіть, будь ласка, текст. Зображення ви можете прикріпити пізніше.")


def save_post(update: Update, context: CallbackContext):
    message: Message = update.message
    job_text: str = message.text

    # Insert raw post to database
    post = Post(text=job_text)
    db.session.add(post)
    db.session.commit()

    _send_job_post(post, send_func=message.reply_text)

    return ConversationHandler.END


def _send_job_post(post: Post, send_func: Callable):
    # build reply text
    keyboards = []

    city_text = 'Змінити місто 🏙️' if post.city_id is not None else 'Додати місто 🏙️'
    button = InlineKeyboardButton(text=city_text, callback_data=f'post.{post.id}.city.page')
    keyboards.append([button])

    position_text = 'Змінити категорію 🤖' if post.position_id is not None else 'Додати категорію 🤖'
    button = InlineKeyboardButton(text=position_text, callback_data=f'post.{post.id}.position.page')
    keyboards.append([button])

    button = InlineKeyboardButton(text='Опублікувати 📨️', callback_data=f'post.{post.id}.publish')
    keyboards.append([button])

    button = InlineKeyboardButton(text='Видалити ❌', callback_data=f'post.{post.id}.delete')
    keyboards.append([button])

    markup = InlineKeyboardMarkup(keyboards, resize_keyboard=True)
    message_text = (
        f"*Вакансія:*\n"
        f"{post.text}\n\n"
    )
    if post.city_id is not None:
        city = City.query.get(post.city_id)
        message_text += f'*Місто:*\n{city.name}\n\n'

    if post.position_id is not None:
        city = Position.query.get(post.position_id)
        message_text += f'*Категорія:*\n{city.name}\n\n'

    if post.is_sent:
        message_text += f'*Статус:* Відправлено ✔️ 🍻 🎉 🍾'
        markup = None

    send_func(
        text=message_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )


def city_page(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)

    update.callback_query.edit_message_text(
        text=(
            "Вкажіть місто публікації вакансії, для цього оберіть один і "
            "з варіантів зі списку нижче. Використовуйте кнопки ⬅️️ та ➡️ для "
            "навігації між сторінками списку"
        ),
        reply_markup=get_cities_keyboard(prefix=f'post.{post_id}.city'),
    )


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

    _send_job_post(post, send_func=update.callback_query.edit_message_text)


def position_page(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)

    update.callback_query.edit_message_text(
        text=(
            "Оберіть одну з категорій для насилання вакансії, для цього оберіть "
            "один із варіантів зі списку нижче. Використовуйте кнопки ⬅️️ та ➡️ для "
            "навігації між сторінками списку"
        ),
        reply_markup=get_positions_keyboard(prefix=f'post.{post_id}.position'),
    )


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

    _send_job_post(post, send_func=update.callback_query.edit_message_text)


def delete_post(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    post = Post.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    update.callback_query.message.delete()


def publish_post(update: Update, context: CallbackContext):
    post_id = _get_post_id(update)
    post = Post.query.get(post_id)

    update.callback_query.edit_message_text('Відправляємо повідомлення ⌛')

    send_post(post)

    _send_job_post(post, send_func=update.callback_query.edit_message_text)


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
                AnyHandler(greeting_fallback),
            ],
            allow_reentry=True,
        )
    )
    dp.add_handler(CommandHandler('stat', get_statistic))

    dp.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('post', create_job)],
            states={
                CREATE_JOB: [MessageHandler(Filters.text, save_post)],
            },
            fallbacks=[AnyHandler(post_fallback)],
            allow_reentry=True,
        ),
    )
    dp.add_handler(CallbackQueryHandler(city_page, pattern=r'post\.\d+\.city\.page'))
    dp.add_handler(CallbackQueryHandler(city_navigate, pattern=r'post\.\d+\.city\.(prev|next)\.\d+'))
    dp.add_handler(CallbackQueryHandler(city_choose, pattern=r'post\.\d+\.city\.\d+'))

    dp.add_handler(CallbackQueryHandler(position_page, pattern=r'post\.\d+\.position\.page'))
    dp.add_handler(CallbackQueryHandler(position_navigate, pattern=r'post\.\d+\.position\.(prev|next)\.\d+'))
    dp.add_handler(CallbackQueryHandler(position_choose, pattern=r'post\.\d+\.position\.\d+'))

    dp.add_handler(CallbackQueryHandler(delete_post, pattern=r'post\.\d+\.delete'))
    dp.add_handler(CallbackQueryHandler(publish_post, pattern=r'post\.\d+\.publish'))
    dp.add_handler(CallbackQueryHandler(print_bad_query))

