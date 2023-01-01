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
from modules.helper import CallbackStatus, MessageStatus, get_customer_last_name_and_order_items


@dp.callback_query_handler(Text(startswith="act:pay-card"), CallbackStatus(2))
async def pay_card(callback: types.CallbackQuery):
    """
    Card payment method handler
    :param callback: Telegram callback object
    """
    await callback.answer("Следуйте инструкции по переводу")
    order_id = int(callback.data.split()[1])
    session = create_session()
    order = session.query(Order).get(order_id)

    await bot.delete_message(order.customer, order.origin_msg)
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("❌ Отменить заказ", callback_data=f"act:cancel_order {order.id}"))
    _, _, order_items = await get_customer_last_name_and_order_items(order)
    origin_msg_text = f"*Ваш заказ № {order.id} ожидает оплаты*\n\n{order_items}\n\n" \
                      f"Сделайте перевод по указанному номеру карты\\.\n" \
                      f"*ВАЖНО\\! Если возможно, в примечании к переводу напишите:*\n\n" \
                      f"`Номер заказа: {order_id}`\n\n" \
                      f"_Номер карты для перевода:_ {STRINGS.card_number}\n\n" \
                      f"После перевода обязательно отправьте " \
                      f"*в ответ на это сообщение* скриншот " \
                      f"экрана подтверждения платежа или фото квитанции, " \
                      f"где видно сумму, дату и время совершения " \
                      f"перевода"
    origin_msg = await bot.send_message(callback.from_user.id,
                                        origin_msg_text,
                                        reply_markup=markup, disable_web_page_preview=True)

    order.origin_msg = origin_msg.message_id
    order.status = 4
    session.commit()


@dp.message_handler(MessageStatus(4), chat_type=ChatType.PRIVATE, content_types=[ContentType.PHOTO])
async def pay_card_check(message: types.Message):
    """
    Card payment check method handler
    :param message: Telegram message object
    """
    if not message.reply_to_message:
        await message.reply("Если Вы отправили фото с квитанцией перевода, то отправьте его заново, "
                            "пожалуйста, так, чтобы оно было ответом на сообщение с инструкцией "
                            "по переводу")
        logging.info("%s user sent a photo without reply_to message", message.from_user.id)
        return

    session = create_session()
    order = session.query(Order).filter(Order.origin_msg == message.reply_to_message.message_id).first()
    if not order:
        await message.reply("Пожалуйста, отправляйте фото в ответ "
                            "на сообщение с инструкциями по переводу")
        logging.info("%s user sent photo in reply to message without order details",
                     message.from_user.id)
        return

    await bot.delete_message(order.customer, order.origin_msg)
    first_name, last_name, order_items = await get_customer_last_name_and_order_items(order)
    origin_msg_text = f"*Ваш заказ № {order.id} ожидает " \
                      f"подтверждения оплаты*\n\n{order_items}\n\n" \
                      f"Наши операторы проверят факт " \
                      f"совершения перевода на нужную сумму\\. " \
                      f"Если средства поступят, мы начнём собирать заказ"
    origin_msg = await bot.send_message(message.from_user.id,
                                        origin_msg_text,
                                        disable_web_page_preview=True)

    await bot.delete_message(-STRINGS.new_orders_chat_id, order.status_msg)
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✅Оплачено", callback_data=f"act:accept-card-payment {order.id}"),
               InlineKeyboardButton("❌НЕ оплачено", callback_data=f"act:deny-card-payment {order.id}"))
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
                      f"Оплата совершена *банковским переводом*\\. На фото — квитанция"
    status_msg = await bot.send_photo(-STRINGS.new_orders_chat_id, photo=message.photo[0].file_id,
                                      caption=status_msg_text, reply_markup=markup)

    order.origin_msg = origin_msg.message_id
    order.status_msg = status_msg.message_id
    order.status = 6
    session.commit()


@dp.callback_query_handler(Text(startswith="act:deny-card-payment"), CallbackStatus(6))
async def deny_card_payment(callback: types.CallbackQuery):
    """
    Deny card payment
    :param callback: Telegram callback object
    """
    order_id = callback.data.split()[1]
    session = create_session()
    order = session.query(Order).get(order_id)

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("❌ Отменить заказ", callback_data=f"act:cancel_order {order.id}"))
    markup.row(InlineKeyboardButton("₿ Криптовалюта", callback_data=f"act:pay-crypto {order.id}"))
    first_name, last_name, order_items = await get_customer_last_name_and_order_items(order)
    origin_msg_text = f"*Ваш перевод по заказу № {order.id} не подтверждён*\n\n{order_items}\n\n" \
                      f"Сделайте перевод по указанному номеру карты\\.\n" \
                      f"*ВАЖНО\\! Если возможно, в примечании к переводу напишите:*\n\n" \
                      f"`Номер заказа: {order_id}`\n\n" \
                      f"_Номер карты для перевода:_ {STRINGS.card_number}\n\n" \
                      f"После перевода обязательно отправьте " \
                      f"*в ответ на это сообщение* скриншот " \
                      f"экрана подтверждения платежа или фото квитанции, " \
                      f"где видно сумму, дату и время совершения " \
                      f"перевода"
    await bot.delete_message(order.customer, order.origin_msg)
    origin_msg = await bot.send_message(callback.from_user.id, origin_msg_text,
                                        reply_markup=markup, disable_web_page_preview=True)

    status_msg_text = f"*Заказ № {order.id}*\n\n" \
                      f"*Клиент\\:* [{first_name} {last_name}]" \
                      f"(tg://user?id={order.customer})\n" \
                      f"*Состав\\:*\n" \
                      f"{order_items}\n\n" \
                      f"*Стоимость:* {order.amount} руб\\.\n" \
                      f"*Комиссия \\({STRINGS.fee}%\\)*: {order.total - order.amount} руб\\.\n" \
                      f"*Итоговая стоимость:* {order.total} руб\\.\n" \
                      f"*Статус:* \\#ожидание\\_оплаты\n\n"
    await bot.edit_message_text(status_msg_text, -STRINGS.new_orders_chat_id, order.status_msg,
                                disable_web_page_preview=True)

    order.status = 4
    order.origin_msg = origin_msg.message_id
    session.commit()
