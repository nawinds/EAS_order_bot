import logging

from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType
from aiogram.types.chat import ChatType
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from modules.bot import dp, bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.orders import Order
from modules.helper import CallbackStatus, MessageStatus, \
    get_customer_last_name_and_order_items, write_us, delete_and_send


@dp.callback_query_handler(Text(startswith="act:pay-crypto"), CallbackStatus(2) | CallbackStatus(4))
async def pay_crypto(callback: types.CallbackQuery):
    """
    Crypto payment method handler
    :param callback: Telegram callback object
    """
    await callback.answer("Следуйте инструкции по переводу")
    order_id = int(callback.data.split()[1])
    session = create_session()
    order = session.query(Order).get(order_id)

    await bot.delete_message(order.customer, order.origin_msg)
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("💳 Банковский перевод", callback_data=f"act:pay-card {order.id}"))
    markup.row(InlineKeyboardButton("❌ Отменить заказ", callback_data=f"act:cancel_order {order.id}"))
    _, _, order_items = await get_customer_last_name_and_order_items(order)
    crypto_wallets_list = "\n".join([f"*{wallet[0]}*: `{wallet[1]}`" for wallet in STRINGS.crypto_wallets])
    origin_msg_text = f"*Ваш заказ № {order.id} ожидает оплаты*\n\n{order_items}\n\n" \
                      f"Сделайте перевод на один из указанных кошельков\\.\n\n" \
                      f"_Доступные кошельки:_\n\n{crypto_wallets_list}\n\n" \
                      f"После перевода обязательно отправьте " \
                      f"*в ответ на это сообщение* TxID " \
                      f"\\(идентификатор транзакции\\)\\. Если возникнут вопросы, {write_us()}"
    origin_msg = await bot.send_message(callback.from_user.id,
                                        origin_msg_text,
                                        reply_markup=markup, disable_web_page_preview=True)

    order.origin_msg = origin_msg.message_id
    order.status = 5
    session.commit()


@dp.message_handler(MessageStatus(5), chat_type=ChatType.PRIVATE)
async def pay_crypto_check(message: types.Message):
    """
    Crypto payment check method handler
    :param message: Telegram message object
    """
    txid = message.text
    session = create_session()
    order = session.query(Order).filter(Order.origin_msg == message.reply_to_message.message_id).first()

    first_name, last_name, order_items = await get_customer_last_name_and_order_items(order)
    origin_msg_text = f"*Ваш заказ № {order.id} ожидает " \
                      f"подтверждения оплаты*\n\n{order_items}\n\n" \
                      f"Наши операторы проверят факт " \
                      f"совершения перевода на нужную сумму\\. " \
                      f"Если средства поступят, мы начнём собирать заказ\\. " \
                      f"В случае возникновения вопросов {write_us()}"

    status_msg_markup = InlineKeyboardMarkup()
    status_msg_markup.row(InlineKeyboardButton("✅Оплачено", callback_data=f"act:accept-payment {order.id}"),
                          InlineKeyboardButton("❌НЕ оплачено", callback_data=f"act:deny-crypto-payment {order.id}"))
    status_msg_text = f"*Заказ № {order.id}*\n\n" \
                      f"*Клиент\\:* [{first_name} {last_name}]" \
                      f"(tg://user?id={order.customer})\n" \
                      f"*Состав\\:*\n" \
                      f"{order_items}\n\n" \
                      f"*Стоимость:* {order.amount} руб\\.\n" \
                      f"*Комиссия \\({STRINGS.fee}%\\)*: {order.total - order.amount} руб\\.\n" \
                      f"*Итоговая стоимость:* {order.total} руб\\.\n" \
                      f"*Статус:* \\#ожидание\\_подтверждения\\_оплаты\n\n" \
                      f"Пожалуйста, проверьте факт совершения оплаты\\.\n" \
                      f"Оплата совершена *криптовалютой*\\.\n" \
                      f"TxID: `{txid}`"
    await delete_and_send(session, order, origin_msg_text, status_msg_text,
                          status_msg_markup=status_msg_markup)

    order.status = 6
    session.commit()


@dp.callback_query_handler(Text(startswith="act:deny-crypto-payment"), CallbackStatus(6))
async def deny_crypto_payment(callback: types.CallbackQuery):
    """
    Deny crypto payment
    :param callback: Telegram callback object
    """
    order_id = callback.data.split()[1]
    session = create_session()
    order = session.query(Order).get(order_id)

    origin_msg_markup = InlineKeyboardMarkup()
    origin_msg_markup.row(InlineKeyboardButton("💳 Банковский перевод", callback_data=f"act:pay-card {order.id}"))
    origin_msg_markup.row(InlineKeyboardButton("❌ Отменить заказ", callback_data=f"act:cancel_order {order.id}"))
    first_name, last_name, order_items = await get_customer_last_name_and_order_items(order)
    crypto_wallets_list = "\n".join([f"*{wallet[0]}*: `{wallet[1]}`" for wallet in STRINGS.crypto_wallets])
    origin_msg_text = f"*Ваш перевод по заказу № {order.id} не подтверждён ❌*\n\n{order_items}\n\n" \
                      f"Сделайте перевод на один из указанных кошельков\\.\n" \
                      f"_Доступные кошельки:_\n\n{crypto_wallets_list}\n\n" \
                      f"После перевода обязательно отправьте " \
                      f"*в ответ на это сообщение* TxID " \
                      f"\\(идентификатор транзакции\\)\\. Если возникнут вопросы, {write_us()}"

    status_msg_text = f"*Заказ № {order.id} \\(оплата не подтверждена\\)*\n\n" \
                      f"*Клиент\\:* [{first_name} {last_name}]" \
                      f"(tg://user?id={order.customer})\n" \
                      f"*Состав\\:*\n" \
                      f"{order_items}\n\n" \
                      f"*Стоимость:* {order.amount} руб\\.\n" \
                      f"*Комиссия \\({STRINGS.fee}%\\)*: {order.total - order.amount} руб\\.\n" \
                      f"*Итоговая стоимость:* {order.total} руб\\.\n" \
                      f"*Статус:* \\#ожидание\\_оплаты\n\n"
    await delete_and_send(session, order, origin_msg_text, status_msg_text,
                          origin_msg_markup=origin_msg_markup)

    order.status = 5
    session.commit()
