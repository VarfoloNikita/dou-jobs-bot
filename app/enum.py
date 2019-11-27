from enum import Enum


class Action(Enum):

    _default = '0' * 50
    start = 'start'
    subscribed = 'subscribed'
    unsubscribe = 'cancel'
    city_added = 'city_added'
    position_added = 'position_added'


class AddSubscriptionStates(Enum):
    city = 'city'
    position = 'position'


class SubscriptionPageState(Enum):
    list = 'list'
    page = 'page'


class Menu(Enum):
    list = 'Мої підписки 📋'
    add = 'Підписатися ➕'
    help = 'Допомога 🙋'
    unsubscribe = 'Відписатися 🔴'

    greeting = 'Змінити привітання 👋'
    stat = 'Статистика 📈'
    post = 'Створити публікацію ✍️'
