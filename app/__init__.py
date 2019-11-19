import atexit
import logging
import os

import telegram.ext
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_dotenv import DotEnv
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', None)
app.config['TELEGRAM_TOKEN'] = os.getenv('TELEGRAM_TOKEN', None)
app.config['HEROKU_APP_NAME'] = os.getenv('HEROKU_APP_NAME', None)
app.config['HEROKU_DOMAIN'] = os.getenv('HEROKU_DOMAIN', None)
if not app.config['SQLALCHEMY_DATABASE_URI']:
    env = DotEnv(app)
    env.alias(maps={'DATABASE_URL': 'SQLALCHEMY_DATABASE_URI'})

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bot = telegram.Bot(token=app.config['TELEGRAM_TOKEN'])
updater = telegram.ext.Updater(bot=bot, use_context=True)
scheduler = BackgroundScheduler()

from app import views
from app import models
from app import handlers
from app import cron

handlers.configure_dispatcher(updater.dispatcher)
cron.configure_scheduler()
