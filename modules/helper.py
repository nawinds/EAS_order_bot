"""
Helper functions and message filters
"""
from aiogram.types import Message

from modules.config import STRINGS


def is_admin(message: Message) -> bool:
    """
    Message filter that checks user to be a bot admin
    :param message: Telegram message object
    :return: True if user is bot admin, else False
    """
    return message.from_user.id in STRINGS.admin_ids


def not_admin(message: Message) -> bool:
    """
    Message filter that checks user not to be a bot admin
    :param message: Telegram message object
    :return: False if user is bot admin, else True
    """
    return not is_admin(message)
