"""
Bot entity and database initialisation
"""
import aiogram

from modules.config import TOKEN, DB_PATH, STATES_DB_PATH
from modules.data.db_session import global_init, create_session
from modules.data.variables import Variable
from modules.sqlite_storage import SQLiteStorage


def db_init():
    """
    Database initialisation and default variables creation
    """
    global_init(DB_PATH)
    session = create_session()
    if not session.query(Variable).filter(Variable.name == "exchange_rate").first():
        session.add(Variable(name="exchange_rate", value="1.0"))
        session.commit()


storage = SQLiteStorage(path=STATES_DB_PATH)
bot = aiogram.Bot(TOKEN, parse_mode=aiogram.types.ParseMode.MARKDOWN_V2)
dp = aiogram.Dispatcher(bot, storage=storage)
