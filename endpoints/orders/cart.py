import asyncio
import logging
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types.chat import ChatType
from aiogram.types.force_reply import ForceReply
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import escape_md

from modules.bot import dp, bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.orders import Order, OrderItem
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
    markup.row(InlineKeyboardButton("✅ Оформить заказ", callback_data="act:checkout"))

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
    markup.row(InlineKeyboardButton("✅ Оформить заказ", callback_data="act:checkout"))

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
    markup.row(InlineKeyboardButton("❌ Отменить заказ", callback_data=f"act:cancel_order {order.id}"))

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
    order.status = 1
    session.commit()
