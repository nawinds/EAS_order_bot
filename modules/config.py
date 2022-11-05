"""
Project configuration module. Loading constants and strings
"""
import json
import logging
import os
from types import SimpleNamespace

TOKEN = os.getenv("TOKEN", None)
DEBUG = os.getenv("DEBUG", None)
LOCAL_PATH = os.getcwd()
DB_PATH = f"{LOCAL_PATH}/modules/data/db/main.db"
AIOGRAM_LOGS_PATH = f"{LOCAL_PATH}/logs/aiogram.log"


if not TOKEN:
    logging.critical("No TOKEN environment variable!")
    raise ValueError("No TOKEN environment variable!")
if not DEBUG:
    logging.critical("No DEBUG environment variable!")
    raise ValueError("No DEBUG environment variable!")
DEBUG = bool(int(DEBUG))

if not os.path.exists(f"{LOCAL_PATH}/logs"):
    os.mkdir(f"{LOCAL_PATH}/logs")
if not os.path.exists(f"{LOCAL_PATH}/modules/data/db"):
    os.mkdir(f"{LOCAL_PATH}/modules/data/db")

with open("strings.json", "r", encoding="utf-8") as strings_file:
    STRINGS = json.loads(strings_file.read(), object_hook=lambda d: SimpleNamespace(**d))
