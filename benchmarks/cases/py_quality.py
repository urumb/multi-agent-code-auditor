import json
import logging

logger = logging.getLogger(__name__)


def add_tag(tag, tags=[]):  # EXPECT: quality
    tags.append(tag)
    return tags


def parse(text):
    try:
        return json.loads(text)
    except:  # EXPECT: quality
        return None


def total(prices):
    discount = 0.1  # EXPECT: quality
    return sum(prices)


def make_handlers(names):
    handlers = []
    for name in names:
        handlers.append(lambda: logger.info(name))  # EXPECT: quality
    return handlers


def describe(user):
    return f"{user['name']} ({user_role})"  # EXPECT: quality
