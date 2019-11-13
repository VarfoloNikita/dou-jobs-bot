from flask import request
from telegram import Update

from app import app, updater


@app.route('/')
def index():
    return "<h1>Welcome to our server !!</h1>"


@app.route('/telegram', methods=['POST', 'OPTIONS'])
def hook():
    data = request.get_json(force=True)
    update = Update.de_json(data, updater.bot)
    updater.dispatcher.process_update(update)

    return 'ok', 200
