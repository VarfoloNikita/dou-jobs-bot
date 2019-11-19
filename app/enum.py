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
