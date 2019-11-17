import atexit

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pytz import utc

from app import scheduler, app
from app.parser import get_new_vacancies
from app.sender import send_vacancies


def configure_scheduler():
    jobstores = {
        'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
    }

    scheduler.add_job(func=job, trigger="interval", minutes=30)
    scheduler.configure(jobstores=jobstores, timezone=utc)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


def job():
    get_new_vacancies()
    send_vacancies()
