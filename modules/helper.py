"""
Helper functions and message filters
"""
import logging

import aiohttp
from aiogram import types
from aiogram.types import Message
from aiohttp.client_exceptions import InvalidURL, ClientConnectorError
from sqlalchemy.orm.session import Session

from modules.config import STRINGS
from modules.data.orders import Order


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


async def validate_url(url: str) -> bool:
    """
    Validates URL to return 200 status code
    :param url: URL to validata
    :return: True if URL is valid, else False
    """
    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout) as httpsession:
        try:
            async with httpsession.get(url) as resp:
                if resp.status != 200:
                    raise ValueError
        except (InvalidURL, ClientConnectorError, ValueError):
            return False
    return True


async def get_order_by_message(message: types.Message, session: Session) -> (Order, None):
    order = session.query(Order).filter(
        Order.status_msg == message.reply_to_message.message_id
    ).first()

    if not order:
        logging.warning("Failed to accept order (reply_to message is not order message)")
        await message.reply("Пожалуйста, отправляйте команду в ответ "
                            "на сообщение с составом заказа")
        return
    return order
