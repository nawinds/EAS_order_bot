import asyncio
import logging
from aiogram import executor
from config import AIOGRAM_LOGS_PATH
from modules.bot import dp


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename=AIOGRAM_LOGS_PATH,
                        format='%(levelname)s %(asctime)s - '
                               '%(name)s (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
    loop = asyncio.get_event_loop()
    executor.start_polling(dp, loop=loop)
