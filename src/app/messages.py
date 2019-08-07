import emoji
import i18n
from i18n import t as _t


# Устанавливаем язык
i18n.set('locale', 'ru')
# Отключаем требование локали в файле перевода
i18n.set('skip_locale_root_data', True)
i18n.load_path.append('app/translations')


def t(*args, **kwargs):
    """
    Функция получения сообщений, дополнительно преобразующая найденные в тексте эмодзи-коды в эмодзи
    :return: Сообщение
    """
    return emoji.emojize(_t(*args, **kwargs))
