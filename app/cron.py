from datetime import timedelta

import requests

from app import parser, sender, db, updater
from app.contants import HOST


def configure_scheduler():
    updater.job_queue.run_repeating(
        callback=get_new_posts,
        interval=timedelta(minutes=5),
    )


def get_new_posts(*args, **kwargs):
    # trigger host for preventing sleeping, can be safety removed on production.
    requests.get(HOST)

    parser.get_new_vacancies()
    sender.dispatch_vacancies()
    sender.send_vacancies()
    db.session.close()
