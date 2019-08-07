import re

import emoji
from telebot.types import User as TelebotUser


def get_full_name(user: TelebotUser):
    """
    Полное имя пользователя телеграм

    :param user:
    :return:
    """
    parts = list()
    parts.append(user.first_name)
    parts.append(user.last_name)
    full_name = " ".join(filter(lambda x: x is not None, parts))
    return full_name if len(full_name) > 0 else '<Empty>'


def find_emoji_in_text(text):
    """
    Возвращает массив эмодзи найденных в строке
    :param text:
    :return:
    """
    # Убираем пробелы, переносы строк, символы слеша (если смайлики будут пересланы из like-бота)
    text = re.sub(r"[\r\n\s\\]", "", text, flags=re.UNICODE)
    chars = list(text)
    emoji_chars = list()
    # В тексте ищем эмодзи, остальные символы игнорируем
    for c in chars:
        if c not in emoji.UNICODE_EMOJI and c not in emoji.UNICODE_EMOJI_ALIAS:
            continue
        emoji_chars.append(c)
    return emoji_chars