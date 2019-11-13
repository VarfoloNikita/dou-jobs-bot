import telegram
import telegram.ext
from flask import Flask
from flask_dotenv import DotEnv
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
env = DotEnv(app)
env.alias(maps={'DATABASE_URL': 'SQLALCHEMY_DATABASE_URI'})

db = SQLAlchemy(app)
migrate = Migrate(app, db)
updater = telegram.ext.Updater(
    token=app.config['TELEGRAM_TOKEN'],
    use_context=True,
)
bot = updater.bot

from app import views
from app import models
from app import handlers


@app.before_first_request
def initialize():
    pass
    # APP_NAME = app.config['HEROKU_APP_NAME']
    # DOMAIN = app.config['HEROKU_DOMAIN']
    # WEB_HOOK_URL = f'https://{APP_NAME}.{DOMAIN}/telegram'
    # print('WEB_HOOK_URL', WEB_HOOK_URL)
    # print(bot.set_webhook(url=WEB_HOOK_URL))
