import os

BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
TOKEN = os.getenv("TOKEN")
LOGGER_TOKEN = os.getenv("LOGGER_TOKEN")
LOCAL_PATH = os.getenv("LOCAL_PATH")
DB_PATH = f"{LOCAL_PATH}/db/main.db"
LOGS_PATH = f"{LOCAL_PATH}/logs/main.log"
AIOGRAM_LOGS_PATH = f"{LOCAL_PATH}/logs/aiogram.log"
