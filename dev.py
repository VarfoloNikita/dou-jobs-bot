import os

from app import updater, bot
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


def set_hook():
    APP_NAME = os.getenv('HEROKU_APP_NAME')
    DOMAIN = os.getenv('HEROKU_DOMAIN')
    WEB_HOOK_URL = f'https://{APP_NAME}.{DOMAIN}/telegram'
    print('WEB_HOOK_URL', WEB_HOOK_URL)
    print(bot.set_webhook(url=WEB_HOOK_URL))


if __name__ == '__main__':
    # Start the Bot
    updater.start_polling()

    logging.info('TELEGRAM BOT was started')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
