"""
Bot endpoints for ordering products
"""
import logging
from math import ceil

from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.types.chat import ChatType
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import escape_md

from modules.bot import dp, bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.orders import Order
from modules.data.variables import Variable
from modules.helper import get_order_by_message, get_customer_last_name_and_order_items, write_us


@dp.callback_query_handler(Text(startswith="act:cancel_order"), chat_type=ChatType.PRIVATE)
async def cancel_order(callback: types.CallbackQuery):
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

    first_name, last_name, order_items = await get_customer_last_name_and_order_items(order)
    text = f"*Ваш заказ № {order.id} ОТМЕНЁН ❌\\!*\n\n{order_items}\n\n"

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
    order = await get_order_by_message(message, session)
    if not order:
        return

    exchange_rate = float(session.query(Variable)
                          .filter(Variable.name == "exchange_rate").first().value)
    price_rub = ceil(price_uan * exchange_rate)
    fee = float(price_rub) * STRINGS.fee / 100
    total_rub = ceil(price_rub + fee)
    fee = str(ceil(fee)).replace('.', '\\.')
    order.amount = price_rub
    order.total = total_rub
    order.status = 2
    session.commit()

    price_formatted = str(price_rub).replace(".", "\\.")
    price_uan = str(price_uan).replace(".", "\\.")
    total_rub = str(total_rub).replace('.', '\\.')

    first_name, last_name, order_items = await get_customer_last_name_and_order_items(order)
    status_msg_text = f"*Заказ № {order.id}*\n\n" \
                      f"*Клиент\\:* [{first_name} {last_name}]" \
                      f"(tg://user?id={order.customer})\n" \
                      f"*Состав\\:*\n" \
                      f"{order_items}\n\n" \
                      f"*Стоимость:* {price_formatted} руб\\. \\({price_uan} юаней\\)\n" \
                      f"*Комиссия \\({STRINGS.fee}%\\)*: {fee} руб\\.\n" \
                      f"*Итого:* {total_rub} руб\\.\n" \
                      f"*Статус:* \\#ожидание\\_оплаты"
    await message.reply_to_message.edit_text(status_msg_text, disable_web_page_preview=True)
    await message.reply(f"Заказу № {order.id} установлена цена в {price_uan} юаней "
                        f"\\= {price_formatted} руб\\. "
                        f"Комиссия \\({STRINGS.fee}%\\): {fee} руб\\.")

    await bot.delete_message(order.customer, order.origin_msg)
    origin_msg_text = f"*Ваш заказ № {order.id} подтверждён ✅\\!*\n\n{order_items}\n\n" \
                      f"Сумма заказа: {price_formatted} руб\\.\n" \
                      f"Комиссия: {fee} руб\\.\n" \
                      f"*Итого к оплате: {total_rub} руб\\.*\n\n" \
                      f"Пожалуйста, выберите способ оплаты ниже и оплатите заказ\\.\n\n" \
                      f"*Список принимаемых криптовалют:*\n" \
                      f"_{', '.join(STRINGS.crypto_list)}_\n\n" \
                      f"По любым вопросам {write_us()}"
    origin_msg_markup = InlineKeyboardMarkup()
    origin_msg_markup.row(InlineKeyboardButton("💳 Банковский перевод", callback_data=f"act:pay-card {order.id}"))
    origin_msg_markup.row(InlineKeyboardButton("₿ Криптовалюта", callback_data=f"act:pay-crypto {order.id}"))
    origin_msg_markup.row(InlineKeyboardButton("❌ Отменить заказ", callback_data=f"act:cancel_order {order.id}"))
    origin_msg = await bot.send_message(order.customer, origin_msg_text,
                                        reply_markup=origin_msg_markup,
                                        disable_web_page_preview=True)
    order.origin_msg = origin_msg.message_id
    session.commit()


@dp.message_handler(chat_type=ChatType.GROUP, commands="deny")
async def deny_order(message: types.Message):
    """
    Deny new order (in admins group chat)
    :param message: Telegram message object
    """
    if not message.reply_to_message:
        logging.debug("User %s failed to deny order (no reply_to message)", message.from_user.id)
        await message.reply("Пожалуйста, отправьте команду в ответ на сообщение с заказом")
        return
    try:
        reason = " ".join(message.text.strip().split()[1:])
        if not reason:
            raise ValueError
    except (IndexError, ValueError):
        logging.debug("User %s failed to deny order (reason not specified)", message.from_user.id)
        await message.reply("Пожалуйста, укажите причину отказа")
        return

    session = create_session()
    order = await get_order_by_message(message, session)
    if not order:
        return

    _, _, order_items = await get_customer_last_name_and_order_items(order)
    await bot.delete_message(-STRINGS.new_orders_chat_id, order.status_msg)
    await message.reply(f"Заказ № {order.id} отклонён")

    origin_msg_text = f"*Ваш заказ № {order.id} ОТКЛОНЁН ❌\\!*\n\n{order_items}\n\n" \
                      f"Причина: {escape_md(reason)}\n\n" \
                      f"Пожалуйста, сделайте новый заказ, приняв во внимание причину отклонения этого\\. " \
                      f"Если у Вас есть вопросы, {write_us()}"
    await bot.delete_message(order.customer, order.origin_msg)
    origin_msg = await bot.send_message(order.customer, origin_msg_text, disable_web_page_preview=True)

    order.origin_msg = origin_msg.message_id
    order.status = 3
    session.commit()
