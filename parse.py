import feedparser

from app.parser import parse_vacancies

url = 'https://jobs.dou.ua/vacancies/feeds/?city=%D0%94%D0%BD%D1%96%D0%BF%D1%80%D0%BE&category=Product%20Manager'
data = feedparser.parse(url)
for vacancy in parse_vacancies(data):
    print(vacancy)
