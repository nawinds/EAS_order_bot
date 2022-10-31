"""
Bot endpoints for getting information
"""
import logging

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
    text = f"Привет\\!\n" \
           f"{STRINGS.start_info}\n" \
           f"Воспользуйся меню ниже, " \
           f"чтобы узнать о нас больше и сделать заказ\\!"

    admin_text = "\n\n\\-\\-\\-\\- *ДЛЯ АДМИНА* \\-\\-\\-\\-\n\n" \
                 "/exchange\\_rate — установить курс с наценкой"
    if is_admin(message):
        text += admin_text

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Информация", callback_data="act:about"),
               InlineKeyboardButton("Отзывы", url=STRINGS.feedback_url))
    markup.row(InlineKeyboardButton("Калькулятор стоимости", callback_data="act:calculator"))
    markup.row(InlineKeyboardButton("Написать нам", url=f"tg://user?id={STRINGS.contact_user_id}"))

    logging.debug("User %s requested a help message", message.from_user.id)
    await message.reply(text, reply_markup=markup)


@dp.callback_query_handler(text="act:about")
@dp.message_handler(commands=["about"])
async def about(callback: types.CallbackQuery):
    """
    /about command handler. Also processes 'about' button from main bot menu.
    Used to get information about company
    :param callback: Telegram callback or message object
    """
    text = f"*Кто мы?*\n" \
           f"{STRINGS.about_info}"

    logging.debug("User %s got about message", callback.from_user.id)
    await callback.answer()
    await bot.send_message(callback.from_user.id, text)


@dp.callback_query_handler(text="act:calculator")
@dp.message_handler(commands=["calculator"])
async def calculator(callback: types.CallbackQuery):
    """
    /calculator command handler. Also processes 'calculator' button from main bot menu.
    Used to calculate price
    :param callback: Telegram callback or message object
    """
    await CalculatorState.price.set()

    session = create_session()
    exchange_rate = session.query(Variable).filter(Variable.name == "exchange_rate").first().value

    text = f"Чтобы узнать, сколько будет стоить у нас товар в рублях, " \
           f"пришлите его цену в юанях, а мы пересчитаем по нашему " \
           f"курсу \\({exchange_rate} руб\\. \\= 1 юань\\)\n\n" \
           f"_Чтобы отменить установку курса, отправьте /cancel_"

    logging.debug("User %s opened calculator", callback.from_user.id)
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
        await message.reply("Укажите только число", reply_markup=ForceReply())
        return

    price_formatted = str(price * exchange_rate).replace('.', '\\.')
    logging.info("User %s calculated price (%s)", message.from_user.id, price * exchange_rate)
    await state.finish()
    await message.reply(f"Стоимость этого товара у нас составит "
                        f"*{price_formatted}* руб\\.")
