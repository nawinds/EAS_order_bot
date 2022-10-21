from modules.config import TOKEN
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import aiogram


bot = aiogram.Bot(TOKEN, parse_mode=aiogram.types.ParseMode.MARKDOWN)
storage = MemoryStorage()
dp = aiogram.Dispatcher(bot, storage=storage)
