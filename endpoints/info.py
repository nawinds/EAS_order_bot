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


class CalculatorState(StatesGroup):
    price = State()


@dp.message_handler(commands=["start", "help"])
async def start_help(message):
    text = f"Привет!\n" \
           f"<some info>\n" \
           f"Воспользуйся меню ниже, " \
           f"чтобы узнать о нас больше и сделать заказ!"

    admin_text = f"\n\n---- *ДЛЯ АДМИНА* ----\n\n" \
                 f"/exchange\\_rate — установить курс с наценкой"
    if is_admin(message):
        text += admin_text

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Информация", callback_data="act:about"),
               InlineKeyboardButton("Отзывы", url="https://instagram.com"))
    markup.row(InlineKeyboardButton("Калькулятор стоимости", callback_data="act:calculator"))
    markup.row(InlineKeyboardButton("Написать нам", url="tg://resolve?domain=nawinds"))

    await message.reply(text, reply_markup=markup)


@dp.callback_query_handler(text="act:about")
@dp.message_handler(commands=["about"])
async def about(callback):
    text = f"*Кто мы?*\n" \
           f"_<Здесь инфа>_"
    await bot.send_message(callback.from_user.id, text)


# @dp.message_handler(commands=["test"])
# async def test_webapp(callback):
#     text = f"Click on the button below to open webapp"
#     markup = InlineKeyboardMarkup()
#     markup.row(InlineKeyboardButton("Click here", web_app=types.WebAppInfo(url="https://pnn.im")))
#     await bot.send_message(callback.from_user.id, text, reply_markup=markup)


@dp.callback_query_handler(text="act:calculator")
@dp.message_handler(commands=["calculator"])
async def calculator(callback):
    exchange_rate = 10

    await CalculatorState.price.set()

    markup = ForceReply(selective=False)
    text = f"Чтобы узнать, сколько будет стоить у нас товар в рублях, " \
           f"пришлите его цену в юанях, а мы пересчитаем по нашему " \
           f"курсу ({exchange_rate} руб. = 1 юань)\n\n" \
           f"_Чтобы отменить установку курса, отправьте /cancel_"
    await bot.send_message(callback.from_user.id, text, reply_markup=ForceReply())


@dp.message_handler(is_admin, state=CalculatorState.price)
async def process_price(message: types.Message, state: FSMContext):
    exchange_rate = 10

    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.reply("Укажите только число", reply_markup=ForceReply())
        return

    print(price * exchange_rate)
    await state.finish()
    await message.reply(f"Стоимость этого товара у нас составит "
                        f"*{price * exchange_rate}* руб.")
