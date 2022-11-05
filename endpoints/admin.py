"""
Bot endpoints for bot admins
"""
import logging

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types.force_reply import ForceReply

from modules.bot import dp
from modules.data.db_session import create_session
from modules.data.variables import Variable
from modules.helper import is_admin


class ExchangeRateState(StatesGroup):
    """
    States of setting exchange rate
    """
    exchange_rate = State()


@dp.message_handler(is_admin, commands="exchange_rate")
async def exchange_rate_command(message: types.Message):
    """
    /exchange_rate command handler. Used for setting new exchange rate by bot admins
    :param message: Telegram message object
    """
    await ExchangeRateState.exchange_rate.set()
    logging.info("User %s is setting exchange rate", message.from_user.id)
    await message.reply("Давайте выставим новый курс\\. "
                        "Сколько будет стоить 1 юань с наценкой?\n\n"
                        "_Чтобы отменить установку курса, отправьте /cancel_",
                        reply_markup=ForceReply())


@dp.message_handler(state="*", commands="cancel")
@dp.message_handler(Text(equals="cancel", ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    /cancel command handler. Used to cancel operations
    (e.g. setting new exchange rate or calculating price)
    :param message: Telegram message object
    :param state: current dialogue state
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("User %s: cancelled state %r", message.from_user.id, current_state)
    await state.finish()
    await message.reply("Действие отменено", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(is_admin, state=ExchangeRateState.exchange_rate)
async def process_exchange_rate(message: types.Message, state: FSMContext):
    """
    New exchange rate processing. Handles messages with float values in
    setting new exchange rate context
    :param message: Telegram message object
    :param state: current dialogue state
    """
    try:
        exchange_rate = float(message.text.replace(",", ".").strip())
    except ValueError:
        logging.info("User %s failed to set a new exchange rate", message.from_user.id)
        await message.reply("Укажите только число\\.\n"
                            "_Чтобы отменить установку курса, "
                            "отправьте /cancel_", reply_markup=ForceReply())
        return

    session = create_session()
    session.query(Variable).filter(Variable.name == "exchange_rate").first().value = exchange_rate
    session.commit()

    logging.info("User %s set a new exchange rate (%s)", message.from_user.id, exchange_rate)
    await state.finish()
    await message.reply("Новый курс установлен\\!")
