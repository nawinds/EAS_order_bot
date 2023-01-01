"""
Helper functions and message filters
"""
import logging
from random import choice

import aiohttp
from aiogram import types
from aiogram.dispatcher.filters import Filter
from aiogram.types import Message
from aiogram.utils.markdown import escape_md
from aiohttp.client_exceptions import InvalidURL, ClientConnectorError
from sqlalchemy.orm.session import Session

from modules.bot import bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.orders import Order


class MessageStatus(Filter):
    """
    Order status checker for message objects
    """
    def __init__(self, status):
        """
        Initialization of order status checker
        :param status: required order status
        """
        self.status = status

    async def check(self, message: types.Message) -> bool:
        """
        Checks if order status equals the status set during initialization
        :param message: Telegram message object
        :return: bool
        """
        session = create_session()
        order = session.query(Order).filter(
            Order.origin_msg == message.reply_to_message.message_id
        ).first()
        return order.status == self.status


class CallbackStatus(Filter):
    """
    Order status checker for callback objects
    """
    def __init__(self, status):
        """
        Initialization of order status checker
        :param status: required order status
        """
        self.status = status

    async def check(self, callback: types.CallbackQuery) -> bool:
        """
        Checks if order status equals the status set during initialization
        :param callback: Telegram callback object
        :return: bool
        """
        order_id = int(callback.data.split()[1])
        session = create_session()
        order = session.query(Order).get(order_id)
        return order.status == self.status


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


async def get_customer_last_name_and_order_items(order: Order) -> (str, list):
    customer_chat = await bot.get_chat(order.customer)
    last_name = customer_chat.last_name if \
        customer_chat.last_name else ""
    order_items = '\n'.join([f"\\- {escape_md(i.url)}" for i in order.items])
    return escape_md(customer_chat.first_name), escape_md(last_name), order_items


async def delete_and_send(session, order, origin_msg_text, status_msg_text,
                          origin_msg_markup=None, status_msg_markup=None):
    await bot.delete_message(order.customer, order.origin_msg)
    origin_msg = await bot.send_message(order.customer, origin_msg_text,
                                        reply_markup=origin_msg_markup, disable_web_page_preview=True)

    await bot.delete_message(-STRINGS.new_orders_chat_id, order.status_msg)
    status_msg = await bot.send_message(-STRINGS.new_orders_chat_id, status_msg_text,
                                        reply_markup=status_msg_markup, disable_web_page_preview=True)
    order.origin_msg = origin_msg.message_id
    order.status_msg = status_msg.message_id
    session.commit()


def write_us(text="пишите нам"):
    contact_user_id = choice(STRINGS.contact_user_id)
    contact_link = f"tg://user?id={contact_user_id}"
    return f"[{text}]({contact_link})"
