import logging

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from modules.bot import dp, bot
from modules.helper import is_admin, not_admin
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.force_reply import ForceReply
from aiogram import md
from modules.config import STRINGS


class CalculatorState(StatesGroup):
    price = State()


@dp.message_handler(commands=["start", "help"])
async def start_help(message: types.Message):
    text = f"Привет\\!\n" \
           f"{STRINGS.start_info}\n" \
           f"Воспользуйся меню ниже, " \
           f"чтобы узнать о нас больше и сделать заказ\\!"

    admin_text = f"\n\n\\-\\-\\-\\- *ДЛЯ АДМИНА* \\-\\-\\-\\-\n\n" \
                 f"/exchange\\_rate — установить курс с наценкой"
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
    text = f"*Кто мы?*\n" \
           f"{STRINGS.about_info}"

    logging.debug("User %s got about message", callback.from_user.id)
    await bot.send_message(callback.from_user.id, text)


@dp.callback_query_handler(text="act:calculator")
@dp.message_handler(commands=["calculator"])
async def calculator(callback: types.CallbackQuery):
    exchange_rate = 10
    await CalculatorState.price.set()

    text = f"Чтобы узнать, сколько будет стоить у нас товар в рублях, " \
           f"пришлите его цену в юанях, а мы пересчитаем по нашему " \
           f"курсу \\({exchange_rate} руб\\. \\= 1 юань\\)\n\n" \
           f"_Чтобы отменить установку курса, отправьте /cancel_"

    logging.debug("User %s opened calculator", callback.from_user.id)
    await bot.send_message(callback.from_user.id, text, reply_markup=ForceReply())


@dp.message_handler(state=CalculatorState.price)
async def process_price(message: types.Message, state: FSMContext):
    exchange_rate = 10

    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        logging.info("User %s failed to calculate price", message.from_user.id)
        await message.reply("Укажите только число", reply_markup=ForceReply())
        return

    price_formatted = str(price * exchange_rate).replace('.', '\\.')
    logging.info("User %s calculated price", message.from_user.id)
    await state.finish()
    await message.reply(f"Стоимость этого товара у нас составит "
                        f"*{price_formatted}* руб\\.")
