import os
import json
from types import SimpleNamespace

# BOT_USERNAME = os.getenv("BOT_USERNAME")
# ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_IDS = tuple(map(int, os.getenv("ADMIN_IDS").split(",")))
TOKEN = os.getenv("TOKEN")
# LOGGER_TOKEN = os.getenv("LOGGER_TOKEN")
LOCAL_PATH = os.getcwd()
# DB_PATH = f"{LOCAL_PATH}/db/main.db"
# LOGS_PATH = f"{LOCAL_PATH}/logs/main.log"
AIOGRAM_LOGS_PATH = f"{LOCAL_PATH}/logs/aiogram.log"

with open("strings.json", "r", encoding="utf-8") as strings_file:
    STRINGS = json.loads(strings_file.read(), object_hook=lambda d: SimpleNamespace(**d))

