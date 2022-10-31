"""
Project configuration module. Loading constants and strings
"""
import json
import os
from types import SimpleNamespace

TOKEN = os.getenv("TOKEN")
LOCAL_PATH = os.getcwd()
DB_PATH = f"{LOCAL_PATH}/modules/data/db/main.db"
AIOGRAM_LOGS_PATH = f"{LOCAL_PATH}/logs/aiogram.log"

if __name__ == 'main':
    with open("strings.json", "r", encoding="utf-8") as strings_file:
        STRINGS = json.loads(strings_file.read(), object_hook=lambda d: SimpleNamespace(**d))
