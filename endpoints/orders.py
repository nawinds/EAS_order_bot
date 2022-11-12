"""
Bot endpoints for ordering products
"""
import logging
from math import ceil
from random import choice
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types.force_reply import ForceReply
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.chat import ChatType

from modules.bot import dp, bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.variables import Variable
from modules.data.orders import Order, OrderItem, OrderStats
from modules.helper import is_admin


class OrderingState(StatesGroup):
    """
    States of calculating price
    """
    first = State()
    product = State()


@dp.callback_query_handler(text="act:order")
@dp.message_handler(chat_type=ChatType.PRIVATE, commands="order")
async def new_order(callback: Union[types.CallbackQuery, types.Message]):
    """
    /order command handler. Also processes 'order' button from main bot menu.
    Used to make new orders
    :param state: current dialogue state
    """
    await OrderingState.first.set()

    text = f"Чтобы сделать заказ\\, отправьте ссылку на товар, который хотите " \
           f"заказать\\.\n\n" \
           f"_Чтобы выйти из режима заказа, отправьте /cancel_"

    logging.debug("User %s started ordering", callback.from_user.id)
    if isinstance(callback, types.CallbackQuery):
        await callback.answer()
    await bot.send_message(callback.from_user.id, text, reply_markup=ForceReply())


@dp.message_handler(chat_type=ChatType.PRIVATE, state=OrderingState.first)
async def create_order(message: types.Message, state: FSMContext):
    """
    Processes first order item (its URL). Creates an order in the DB.
    :param state: current dialogue state
    :param message: Telegram message object
    """
    session = create_session()
    order = Order(customer=message.from_user.id)
    session.add(order)
    session.commit()

    async with state.proxy() as data:
        data['order_id'] = order.id

    order.items.append(OrderItem(url=message.text))
    session.commit()

    await OrderingState.next()

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Оформить заказ", callback_data="act:checkout"))

    text = f"*Корзина*:\n\n\\- {message.text}\n\n" \
           f"Если Вы хотите добавить в заказ ещё один товар, отправьте ссылку на него\\. " \
           f"Чтобы закончить оформление заказа, нажмите на кнопку под этим сообщением\\." \
           f"_Чтобы выйти из режима заказа, отправьте /cancel_"

    logging.debug("User %s created %s order by adding item", message.from_user.id, order.id)
    await message.answer(text, reply_markup=markup)


@dp.message_handler(chat_type=ChatType.PRIVATE, state=OrderingState.product)
async def add_item(message: types.Message, state: FSMContext):
    """
    Processes order items (their URLs).
    :param state: current dialogue state
    :param message: Telegram message object
    """
    session = create_session()
    async with state.proxy() as data:
        order = session.query(Order).get(data['order_id'])

    order.items.append(OrderItem(url=message.text))
    session.commit()

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Оформить заказ", callback_data="act:checkout"))

    order_items = '\n'.join([f"\\- {i.url}" for i in order.items])

    text = f"*Корзина*:\n\n{order_items}\n\n" \
           f"Если Вы хотите добавить в заказ ещё один товар, отправьте ссылку на него\\. " \
           f"Чтобы закончить оформление заказа, нажмите на кнопку под этим сообщением\\." \
           f"_Чтобы выйти из режима заказа, отправьте /cancel_"

    logging.debug("User %s added %s order item", message.from_user.id, order.id)
    await message.answer(text, reply_markup=markup)


@dp.callback_query_handler(chat_type=ChatType.PRIVATE, text="act:checkout", state=OrderingState.product)
async def checkout(callback: types.CallbackQuery, state: FSMContext):
    """
    Order checkout.
    :param state: current dialogue state
    :param callback: Telegram callback object
    """
    session = create_session()
    async with state.proxy() as data:
        order = session.query(Order).get(data['order_id'])
    await state.finish()

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Отменить заказ", callback_data=f"act:cancel_order {order.id}"))

    order_items = '\n'.join([f"\\- {i.url}" for i in order.items])

    text = f"*Ваш заказ №{order.id}*:\n\n{order_items}\n\n" \
           f"Мы постаемся как можно быстрее рассмотреть Ваш заказ и " \
           f"определить его итоговую стоимость в рублях\\. " \
           f"Когда мы всё посчитаем, Вам придёт сообщение с суммой заказа и реквизитами для оплаты"

    logging.debug("User %s checkouted %s order", callback.from_user.id, order.id)
    await callback.answer()
    origin_message = await bot.send_message(callback.from_user.id, text, reply_markup=markup)
    last_name = callback.from_user.last_name if callback.from_user.last_name else ""
    new_order_text = f"*Новый заказ \\(№ {order.id}\\)*\n\n" \
                     f"*Клиент\\:* [{callback.from_user.first_name} {last_name}]" \
                     f"(tg://user?id={callback.from_user.id})\n" \
                     f"*Состав\\:*\n" \
                     f"{order_items}\n\n" \
                     f"Пожалуйста\\, сходите по ссылкам\\, удостоверьтесь, " \
                     f"что заказ можно обработать и рассчитайте его сумму в юанях\\. " \
                     f"В ответ на это сообщение отправьте\n" \
                     f"/accept 123\\, где 123 — сумма заказа в юанях или\n" \
                     f"/deny reason\\, где reason — причина отказа обработать заказ"
    new_order_message = await bot.send_message(-STRINGS.new_orders_chat_id, new_order_text)
    order.origin_msg = origin_message.message_id
    order.new_msg = new_order_message.message_id
    order.status += 1
    session.commit()
