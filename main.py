"""
A Telegram bot for ordering things from Chinese sites
"""
import asyncio
import logging

from aiogram import executor

from modules.bot import dp, db_init
from modules.config import AIOGRAM_LOGS_PATH, DEBUG
import endpoints

if __name__ == '__main__':
    if not DEBUG:
        logging.basicConfig(level=logging.INFO, filename=AIOGRAM_LOGS_PATH,
                            format='%(levelname)s %(asctime)s - '
                                   '%(name)s (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
    logging.info("Starting...")
    db_init()
    loop = asyncio.get_event_loop()
    executor.start_polling(dp, loop=loop)
