import logging

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from modules.bot import dp, bot
from modules.helper import is_admin
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types.force_reply import ForceReply


class ExchangeRateState(StatesGroup):
    exchange_rate = State()


@dp.message_handler(is_admin, commands="exchange_rate")
async def exchange_rate_command(message: types.Message):
    await ExchangeRateState.exchange_rate.set()
    logging.info("User %s is setting exchange rate", message.from_user.id)
    await message.reply("Давайте выставим новый курс\\. "
                        "Сколько будет стоить 1 юань с наценкой?\n\n"
                        "_Чтобы отменить установку курса, отправьте /cancel_",
                        reply_markup=ForceReply())


@dp.message_handler(state="*", commands="cancel")
@dp.message_handler(Text(equals="cancel", ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("User %s: cancelled state %r", message.from_user.id, current_state)
    await state.finish()
    await message.reply("Действие отменено", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(is_admin, state=ExchangeRateState.exchange_rate)
async def process_exchange_rate(message: types.Message, state: FSMContext):
    try:
        exchange_rate = float(message.text.replace(",", ".").strip())
    except ValueError:
        logging.info("User %s failed to set a new exchange rate", message.from_user.id)
        await message.reply("Укажите только число", reply_markup=ForceReply())
        return

    logging.info("User %s set a new exchange rate", message.from_user.id)
    await state.finish()
    await message.reply("Новый курс установлен\\!")
