"""
Bot endpoints for ordering products
"""
import asyncio
import logging
from math import ceil
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types.chat import ChatType
from aiogram.types.force_reply import ForceReply
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import escape_md

from modules.bot import dp, bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.orders import Order, OrderItem
from modules.data.variables import Variable
from modules.helper import validate_url


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
    :param callback: Telegram callback or message object
    """
    await OrderingState.first.set()

    text = "Чтобы сделать заказ\\, отправьте ссылку на товар, который хотите " \
           "заказать\\.\n\n" \
           "_Чтобы выйти из режима заказа, отправьте /cancel_"

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

    url = message.text
    if not await validate_url(url):
        logging.debug("User %s failed to create order by adding item",
                      message.from_user.id)
        text = "Пожалуйста, введите существующую ссылку\n\n" \
               "_Чтобы выйти из режима заказа, отправьте /cancel_"
        alert_message = await message.reply(text)
        await asyncio.sleep(4)
        await alert_message.delete()
        await message.delete()
        return
    session = create_session()
    order = Order(customer=message.from_user.id)
    session.add(order)
    session.commit()

    async with state.proxy() as data:
        data["order_id"] = order.id

    order.items.append(OrderItem(url=url))
    session.commit()

    await OrderingState.next()

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Оформить заказ", callback_data="act:checkout"))

    text = f"*Корзина*:\n\n\\- {escape_md(url)}\n\n" \
           f"Если Вы хотите добавить в заказ ещё один товар, отправьте ссылку на него\\. " \
           f"Чтобы закончить оформление заказа, нажмите на кнопку под этим сообщением\\.\n\n" \
           f"_Чтобы выйти из режима заказа, отправьте /cancel_"

    logging.debug("User %s created %s order by adding item", message.from_user.id, order.id)
    cart_msg = await message.answer(text, reply_markup=markup, disable_web_page_preview=True)
    await message.delete()
    async with state.proxy() as data:
        data["cart_msg"] = str(cart_msg.chat.id) + " " + str(cart_msg.message_id)


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
        cart_msg = data["cart_msg"].split()

    url = message.text
    if not await validate_url(url):
        logging.debug("User %s failed to create %s order by adding item",
                      message.from_user.id, order.id)
        text = "Пожалуйста, введите существующую ссылку\n\n" \
               "_Чтобы выйти из режима заказа, отправьте /cancel_"
        alert_message = await message.reply(text)
        await asyncio.sleep(4)
        await alert_message.delete()
        await message.delete()
        return
    order.items.append(OrderItem(url=url))
    session.commit()

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Оформить заказ", callback_data="act:checkout"))

    order_items = '\n'.join([f"\\- {escape_md(i.url)}" for i in order.items])

    text = f"*Корзина*:\n\n{order_items}\n\n" \
           f"Если Вы хотите добавить в заказ ещё один товар, отправьте ссылку на него\\. " \
           f"Чтобы закончить оформление заказа, нажмите на кнопку под этим сообщением\\.\n\n" \
           f"_Чтобы выйти из режима заказа, отправьте /cancel_"

    logging.debug("User %s added %s order item", message.from_user.id, order.id)
    await bot.edit_message_text(text, *cart_msg, reply_markup=markup, disable_web_page_preview=True)
    await message.delete()


@dp.callback_query_handler(chat_type=ChatType.PRIVATE,
                           text="act:checkout", state=OrderingState.product)
async def checkout(callback: types.CallbackQuery, state: FSMContext):
    """
    Order checkout.
    :param state: current dialogue state
    :param callback: Telegram callback object
    """
    session = create_session()
    async with state.proxy() as data:
        order = session.query(Order).get(data["order_id"])
        await bot.delete_message(*data["cart_msg"].split())
    await state.finish()

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Отменить заказ", callback_data=f"act:cancel_order {order.id}"))

    order_items = '\n'.join([f"\\- {escape_md(i.url)}" for i in order.items])

    text = f"*Ваш заказ № {order.id} оформлен ✅\\!*\n\n{order_items}\n\n" \
           f"Мы постаемся как можно быстрее рассмотреть Ваш заказ и " \
           f"определить его итоговую стоимость в рублях\\. " \
           f"Когда мы всё посчитаем, Вам придёт сообщение с суммой заказа и реквизитами для оплаты"

    logging.debug("User %s checkouted %s order", callback.from_user.id, order.id)
    await callback.answer()
    origin_message = await bot.send_message(callback.from_user.id, text, reply_markup=markup,
                                            disable_web_page_preview=True)
    last_name = callback.from_user.last_name if callback.from_user.last_name else ""
    new_order_text = f"*Новый заказ \\(№ {order.id}\\)*\n\n" \
                     f"*Клиент\\:* [{callback.from_user.first_name} {last_name}]" \
                     f"(tg://user?id={callback.from_user.id})\n" \
                     f"*Состав\\:*\n" \
                     f"{order_items}\n\n" \
                     f"*Статус*: \\#новый\\_заказ\n\n" \
                     f"Пожалуйста\\, сходите по ссылкам\\, удостоверьтесь, " \
                     f"что заказ можно обработать и рассчитайте его сумму в юанях\\. " \
                     f"В ответ на это сообщение отправьте\n" \
                     f"/accept 123\\, где 123 — сумма заказа в юанях или\n" \
                     f"/deny reason\\, где reason — причина отказа обработать заказ"
    new_order_message = await bot.send_message(-STRINGS.new_orders_chat_id, new_order_text,
                                               disable_web_page_preview=True)
    order.origin_msg = origin_message.message_id
    order.status_msg = new_order_message.message_id
    order.status += 1
    session.commit()


@dp.callback_query_handler(Text(contains="act:cancel_order"), chat_type=ChatType.PRIVATE)
async def cancel(callback: types.CallbackQuery):
    """
    Cancel order
    :param callback: Callback or message Telegram object
    """
    order_id = callback.data.split()[1]
    session = create_session()
    order = session.query(Order).get(order_id)
    for i in order.items:
        session.delete(i)
    session.delete(order)
    session.commit()
    logging.debug("User %s cancelled %s order", callback.from_user.id, order.id)
    await callback.answer("Заказ отменён!")
    await bot.send_message(callback.from_user.id, f"Заказ {order_id} отменён\\!")

    last_name = callback.from_user.last_name if callback.from_user.last_name else ""
    order_items = '\n'.join([f"\\- {escape_md(i.url)}" for i in order.items])
    text = f"*Ваш заказ № {order.id} ОТМЕНЁН ❌\\!*\n\n{order_items}\n\n" \
           f"Мы постаемся как можно быстрее рассмотреть Ваш заказ и " \
           f"определить его итоговую стоимость в рублях\\. " \
           f"Когда мы всё посчитаем, Вам придёт сообщение с суммой заказа и реквизитами для оплаты"

    await callback.message.edit_text(text, disable_web_page_preview=True)
    await bot.send_message(-STRINGS.new_orders_chat_id,
                           f"[{callback.from_user.first_name} {last_name}]"
                           f"(tg://user?id={callback.from_user.id}) "
                           f"отменил заказ № {order.id}")
    await bot.delete_message(-STRINGS.new_orders_chat_id, order.status_msg)


@dp.message_handler(chat_type=ChatType.GROUP, commands="accept")
async def accept_order(message: types.Message):
    """
    Accept new order (in admins group chat)
    :param message: Telegram message object
    """
    if not message.reply_to_message:
        logging.debug("User %s failed to accept order (no reply_to message)", message.from_user.id)
        await message.reply("Пожалуйста, отправьте команду в ответ на сообщение с заказом")
        return
    try:
        price_uan = float(message.text.replace(",", ".").strip().split()[1])
    except (IndexError, ValueError):
        logging.debug("User %s failed to accept order (amount not specified)", message.from_user.id)
        await message.reply("Пожалуйста, укажите сумму заказа в юанях")
        return

    session = create_session()
    order = session.query(Order).filter(
        Order.status_msg == message.reply_to_message.message_id
    ).first()

    if not order:
        logging.warning("Failed to accept order (reply_to message is not order message)")
        await message.reply("Пожалуйста, отправляйте команду в ответ "
                            "на сообщение с составом заказа")
        return

    exchange_rate = float(session.query(Variable)
                          .filter(Variable.name == "exchange_rate").first().value)
    price_rub = ceil(price_uan * exchange_rate)
    fee = float(price_rub) * STRINGS.fee / 100
    total_rub = str(ceil(price_rub + fee)).replace('.', '\\.')
    fee = str(ceil(fee)).replace('.', '\\.')
    order.amount = price_rub
    order.status += 1
    session.commit()

    price_formatted = str(price_rub).replace(".", "\\.")
    price_uan = str(price_uan).replace(".", "\\.")

    customer_chat = await bot.get_chat(order.customer)
    last_name = customer_chat.last_name if \
        customer_chat.last_name else ""
    order_items = '\n'.join([f"\\- {escape_md(i.url)}" for i in order.items])
    order_text = f"*Заказ № {order.id}*\n\n" \
                 f"*Клиент\\:* [{customer_chat.first_name} {last_name}]" \
                 f"(tg://user?id={order.customer})\n" \
                 f"*Состав\\:*\n" \
                 f"{order_items}\n\n" \
                 f"*Стоимость:* {price_formatted} руб\\. \\({price_uan} юаней\\)\n" \
                 f"*Комиссия \\({STRINGS.fee}%\\)*: {fee} руб\\.\n" \
                 f"*Итого:* {total_rub} руб\\.\n" \
                 f"*Статус:* \\#ожидание\\_оплаты"
    await message.reply_to_message.edit_text(order_text, disable_web_page_preview=True)
    await message.reply(f"Заказу № {order.id} установлена цена в {price_uan} юаней "
                        f"\\= {price_formatted} руб\\. "
                        f"Комиссия \\({STRINGS.fee}%\\): {fee} руб\\.")
    await bot.delete_message(order.customer, order.origin_msg)
    text = f"*Ваш заказ № {order.id} подтверждён ✅\\!*\n\n{order_items}\n\n" \
           f"Сумма заказа: {price_formatted} руб\\.\n" \
           f"Комиссия: {fee} руб\\.\n" \
           f"*Итого к оплате: {total_rub} руб\\.*\n\n" \
           f"Пожалуйста, выберите способ оплаты ниже и оплатите заказ\\."
    origin_msg = await bot.send_message(order.customer, text, disable_web_page_preview=True)
    order.origin_msg = origin_msg
    session.commit()
