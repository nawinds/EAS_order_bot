"""
Bot endpoints for getting information
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

from modules.bot import dp, bot
from modules.config import STRINGS
from modules.data.db_session import create_session
from modules.data.variables import Variable
from modules.helper import is_admin


class CalculatorState(StatesGroup):
    """
    States of calculating price
    """
    price = State()


@dp.message_handler(commands=["start", "help"])
async def start_help(message: types.Message):
    """
    /start and /help command handler.
    Used for getting user menu and information about bot usage
    :param message: Telegram message object
    """
    text = STRINGS.start_info

    admin_text = "\n\n\\-\\-\\-\\- *ДЛЯ АДМИНА* \\-\\-\\-\\-\n\n" \
                 "/exchange\\_rate — установить курс с наценкой"
    if is_admin(message):
        text += admin_text

    contact_user_id = choice(STRINGS.contact_user_id)
    if contact_user_id == 452987344:
        contact_link = f"tg://resolve?domain=zhelninartem"
    else:
        contact_link = f"tg://user?id={contact_user_id}"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("ℹ️ Информация", callback_data="act:about"),
               InlineKeyboardButton("💬 Отзывы", url=STRINGS.feedback_url))
    markup.row(InlineKeyboardButton("💴 Калькулятор стоимости", callback_data="act:calculator"))
    markup.row(InlineKeyboardButton("🧑‍🔧 Сделать заказ", url=contact_link))

    logging.debug("User %s requested a help message", message.from_user.id)
    await message.reply(text, reply_markup=markup)


@dp.callback_query_handler(text="act:about")
@dp.message_handler(commands=["about"])
async def about(callback: Union[types.CallbackQuery, types.Message]):
    """
    /about command handler. Also processes 'about' button from main bot menu.
    Used to get information about company
    :param callback: Telegram callback or message object
    """
    text = STRINGS.about_info

    logging.debug("User %s got about message", callback.from_user.id)
    if isinstance(callback, types.CallbackQuery):
        await callback.answer()
    await bot.send_message(callback.from_user.id, text)


@dp.callback_query_handler(text="act:calculator")
@dp.message_handler(commands=["calculator"])
async def calculator(callback: Union[types.CallbackQuery, types.Message]):
    """
    /calculator command handler. Also processes 'calculator' button from main bot menu.
    Used to calculate price
    :param callback: Telegram callback or message object
    """
    await CalculatorState.price.set()

    session = create_session()
    exchange_rate = str(session.query(Variable)
                        .filter(Variable.name == "exchange_rate").first().value).replace(".", "\\.")

    text = f"Чтобы узнать, сколько будет стоить у нас товар в рублях, " \
           f"пришлите его цену в юанях, а мы пересчитаем по нашему " \
           f"курсу \\(*{exchange_rate} руб\\. \\= 1 юань*\\)\n\n" \
           f"_Чтобы выйти из режима калькулятора, отправьте /cancel_"

    logging.debug("User %s opened calculator", callback.from_user.id)
    if isinstance(callback, types.CallbackQuery):
        await callback.answer()
    await bot.send_message(callback.from_user.id, text, reply_markup=ForceReply())


@dp.message_handler(state=CalculatorState.price)
async def process_price(message: types.Message, state: FSMContext):
    """
    Chinese products price handler. Used to convert CNY to RUB.
    :param message: Telegram message object
    :param state: current dialogue state
    """
    session = create_session()
    exchange_rate = float(session.query(Variable)
                          .filter(Variable.name == "exchange_rate").first().value)

    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        logging.info("User %s failed to calculate price", message.from_user.id)
        await message.reply("Укажите только число\\.\n"
                            "_Чтобы выйти из режима калькулятора, "
                            "отправьте /cancel_", reply_markup=ForceReply())
        return

    price_formatted = str(ceil(price * exchange_rate)).replace('.', '\\.')
    logging.info("User %s calculated price (%s)", message.from_user.id, price * exchange_rate)
    await state.finish()
    await message.reply(f"Стоимость этого товара у нас составит "
                        f"*{price_formatted}* руб\\.")
