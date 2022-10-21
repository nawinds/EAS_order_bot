from modules.config import ADMIN_IDS


def is_admin(message):
    return True if message.from_user.id in ADMIN_IDS else False


def not_admin(message):
    return not is_admin(message)
