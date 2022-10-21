import asyncio
import logging
from aiogram import executor
from modules.config import AIOGRAM_LOGS_PATH
from modules.bot import dp, bot
import endpoints


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,  # filename=AIOGRAM_LOGS_PATH,
                        format='%(levelname)s %(asctime)s - '
                               '%(name)s (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
    logging.info("Starting...")
    loop = asyncio.get_event_loop()
    executor.start_polling(dp, loop=loop)
