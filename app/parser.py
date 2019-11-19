import re
import ssl
from datetime import datetime
from typing import Iterator
from urllib.parse import quote

import feedparser
from bs4 import BeautifulSoup

from app import db, app
from app.models import Subscription, City, Position, Vacancy, VacancyParameters

ssl._create_default_https_context = ssl._create_unverified_context

URL = 'https://jobs.dou.ua/vacancies/feeds/?'

MESSAGE_LIMIT = 4095


def remove_markdown_symbols(text):
    return (
        text.replace('*', '').replace(']', '').replace('[', '')
        .replace('_', '').replace('`', '')
    )


def escape_markdown_symbols(text):
    return (
        text.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("`", "\\`")
    )


def build_feed_url(city: City, position: Position) -> str:
    return safe_url(f'{URL}{position.param}&{city.param}')


def safe_url(url):
    return quote(url, safe='/:?=&')


def get_block_text(soup: BeautifulSoup, class_: str):
    requirements = soup.find("div", {"class": class_})
    if not requirements:
        return None

    raw_text = requirements.find("div", {"class": 'text'})
    if not raw_text:
        return None

    for match in raw_text.findAll('span'):
        match.unwrap()

    for br in raw_text.find_all("br"):
        br.replace_with("\n")

    text = raw_text.get_text()
    text = re.sub(r'[ \t]+', r' ', text)
    text = re.sub(r'\n+', r'\n', text)
    text = escape_markdown_symbols(text)
    return text.strip()


def prepare_text(text: str):
    soup = BeautifulSoup(text, 'html.parser')
    requirements = get_block_text(soup, 'requirements')
    skills = get_block_text(soup, 'additionalskils')
    bonuses = get_block_text(soup, 'bonuses')
    duty = get_block_text(soup, 'duty')
    project = get_block_text(soup, 'project')

    # vacancy text in telegram markdown
    result = ''
    if requirements:
        result += f"*Необхідні навички*\n{requirements}\n\n"
    if skills:
        result += f"*Буде плюсом*\n{skills}\n\n"
    if bonuses:
        result += f"*Пропонуємо*\n{bonuses}\n\n"
    if duty:
        result += f"*Обов\'язки*\n{duty}\n\n"
    if project:
        result += f"*Про проект*\n{project}\n\n"
    return result


def parse_vacancies(data: feedparser.FeedParserDict) -> Iterator[Vacancy]:
    for entry in data.get('entries', []):
        try:
            year, month, day, hour, minutes, seconds, *_ = entry.published_parsed
            date = datetime(year, month, day, hour, minutes, seconds)
            text = prepare_text(entry.description)
            url = entry.link
        except Exception as exception:
            app.logger.exception(
                msg='Exception during parsing job post',
                exc_info=exception,
            )
            continue
        title = remove_markdown_symbols(entry.title)
        text = f'*{title}*\n\n' + text
        link = f'*Посилання*\n[{title}]({entry.link})'

        result = text + link
        if len(result) > MESSAGE_LIMIT:
            strip_to = MESSAGE_LIMIT - len(link) - 10
            result = text[:strip_to] + '...\n\n' + link

        yield Vacancy(url=url, title=entry.title, text=result, date=date)


def update_new_vacancies(city: City, position: Position):
    app.logger.info(f'Get feed for {city.name}, {position.name}')

    url = build_feed_url(city, position)
    data = feedparser.parse(url)
    for vacancy in parse_vacancies(data):
        vacancy = vacancy.soft_add()

        # insert new vacancy parameters
        parameters = VacancyParameters(
            city_id=city.id,
            position_id=position.id,
            vacancy_id=vacancy.id,
        )
        if parameters.exists():
            app.logger.info('Skip entire feed such as vacancy exists')
            break

        db.session.add(parameters)
        db.session.commit()
        app.logger.info(f'New vacancy was added: {vacancy.title}')


def get_new_vacancies():
    subscriptions = (
        db.session.query(Subscription, Position, City).join(Position).join(City)
        .distinct(Subscription.position_id, Subscription.city_id).all()
    )

    for subscription, position, city in subscriptions:
        update_new_vacancies(city, position)
