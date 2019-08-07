"""
Логика бота
"""

import json
import logging

from telebot import TeleBot, apihelper, logger
from telebot.types import Message as TelebotMessage, Chat as TelebotChat, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from app import config, repo, db, utils
from app.messages import t

# Если конфигурация содержит прокси, то включаем прокси в телеботе
from app.models import AdminState, Suggestion
from app.utils import get_full_name

if config.APP_BOT_PROXY is not None:
    apihelper.proxy = {"https": config.APP_BOT_PROXY}

# Включаем логгер
logger.setLevel(logging.DEBUG)

# Создаем экземпляр бота
bot = TeleBot(config.APP_BOT_TOKEN)

# Действия нажатий на кнопки при сообщениях имеют максимально кракий вид, чтобы занимать меньше места
# в нагрузке кнопки (Телеграм позволяет передавать вместе с кнопкой только 64 байта информации)
ACTION_ACCEPT = "a"
"""
Запостить
"""
ACTION_ACCEPT_WITH_POLL = "p"
"""
Запостить с опросом
"""
ACTION_DECLINE = "d"
"""
Отклонить
"""
ACTION_VOTE = "v"
"""
Проголосовать
"""

ADMIN_SUGGESTION_ACTIONS = [ACTION_ACCEPT,
                            ACTION_ACCEPT_WITH_POLL,
                            ACTION_DECLINE]
"""
Админские действия над предложкой
"""
VOTE_ACTIONS = [ACTION_VOTE]
"""
Действия с голосами
"""

# Решения админа
DECISION_ACCEPT = "decision_accept"
"""
Пост принят
"""
DECISION_ACCEPT_WITH_POLL = "decision_accept_with_poll"
"""
Пост принят и добавлен опрос
"""
DECISION_DECLINE = "decision_decline"
"""
Пост отклонен
"""


def get_admin_id():
    chat = bot.get_chat(config.APP_BOT_ADMIN_ID)
    if chat is None:
        raise Exception("Admin fetching error")
    return chat.id


def get_channel() -> TelebotChat:
    """
    Получить канал в который предлагаются посты

    :return: Канал, в который предлагаются посты
    :rtype: TelegramChat
    """
    channel = bot.get_chat(config.APP_CHANNEL_ID)
    if channel is None:
        raise Exception("Channel not found")
    return channel


def generate_post_link(message_id) -> str:
    """
    Генерирует ссылку на пост в канале

    :param message_id: Идентификатор сообщения
    :return: Ссылка на пост
    """
    channel = get_channel()
    return "https://t.me/%(channel_url)s/%(message_id)d" % {
        "channel_url": channel.username,
        "message_id": message_id
    }


def render_decision(decision: str) -> str:
    """
    Создает отображение решениения с предложкой

    :param decision: Решение (см. константы)
    :return:
    """
    if decision == DECISION_ACCEPT:
        return t("app.admin.decision.accepted.rich")
    elif decision == DECISION_ACCEPT_WITH_POLL:
        return t("app.admin.decision.accepted_with_poll.rich")
    elif decision == DECISION_DECLINE:
        return t("app.admin.decision.declined.rich")
    else:
        raise Exception("Unknown decision")


def render_post_url(channel_message_id: int):
    """
    Создает отображение ссылки на пост

    :param channel_message_id: Идентификатор поста в канале
    """
    post_url = generate_post_link(channel_message_id)
    post_link_caption = t("app.admin.suggestion.post_url", url=post_url)
    return post_link_caption


def render_suggestion_text(suggestion: Suggestion):
    """
    Создает текст предложки

    :param suggestion: Предложка
    :return: Тест предложки
    """
    # Основа: заголовок и отправитель
    text = t("app.admin.suggestion.head")
    text += "\n\n"
    # Проверить будет ли работать ссылка на пользователя без юзернейма
    # if not suggestion.user_is_public():
    #     # Отправитель не имеет юзернейма
    #     text += messages.SUGGESTION_FROM % {
    #         "user_title": suggestion.user_title
    #     }
    # else:
    # # Отправитель публичен
    text += t("app.admin.suggestion.from.url",
              user_id=suggestion.user_id,
              user_title=suggestion.user_title)
    # Если отправитель переслал пост из другого канала или от другого пользователя,
    # добавляем информацию об этом в предложку
    if suggestion.is_forward():
        text += "\n"
        if not suggestion.forwarded_is_public():
            # Автор исходного поста не имеет юзернейма
            text += t("app.admin.suggestion.forwarded_from.plain",
                      forwarded_user_title=suggestion.forwarded_from_title)
        else:
            # Автор исходного поста публичен
            text += t("app.admin.suggestion.forwarded_from.url",
                      forwarded_user_id=suggestion.forwarded_from_username,
                      forwarded_user_title=suggestion.forwarded_from_title)
    # Если по предложке уже есть решение, то отображаем его
    if suggestion.decision is not None:
        text += "\n\n"
        text += render_decision(suggestion.decision)
        # Если есть ссылка на пост, то добавляем ее
        # Ссылка на пост может быть только если есть решение
        if suggestion.channel_post_id is not None:
            text += "\n"
            text += render_post_url(suggestion.channel_post_id)
    return text


def rerender_suggestion(suggestion: Suggestion, reply_markup: InlineKeyboardMarkup = None):
    """
    Обновляет текст предложки

    :param suggestion: Предложка
    :param reply_markup Кнопки при необходимости
    """
    admin_id = get_admin_id()
    suggestion_text = render_suggestion_text(suggestion)
    bot.edit_message_caption(suggestion_text,
                             admin_id,
                             suggestion.admin_message_id,
                             parse_mode="HTML",
                             reply_markup=reply_markup)


@db.flush_session
def reset_suggestion(suggestion: Suggestion, session=None):
    """
    Восстанавливает предложку в состояние новой
    :param suggestion:
    :return:
    """
    suggestion.reset_to_new()
    markup = create_admin_reply_markup(suggestion)
    rerender_suggestion(suggestion, markup)


def create_admin_reply_markup(suggestion: Suggestion):
    """
    Создает кнопки для сообщения предложки

    :return: Кнопки
    """
    markup = InlineKeyboardMarkup()
    # В каждой кноке сохраняем информацию о действии, запоминаем идентификатор пользователя отправителя
    # и идентификатор сообщения отправителя в чате с ботом
    markup.add(InlineKeyboardButton(t("app.admin.suggestion.button.accept"),
                                    callback_data=json.dumps({
                                        'a': ACTION_ACCEPT,
                                        's': suggestion.id,
                                    })))
    markup.add(InlineKeyboardButton(t("app.admin.suggestion.button.accept_with_poll"),
                                    callback_data=json.dumps({
                                        'a': ACTION_ACCEPT_WITH_POLL,
                                        's': suggestion.id,
                                    })))
    markup.add(InlineKeyboardButton(t("app.admin.suggestion.button.decline"),
                                    callback_data=json.dumps({
                                        'a': ACTION_DECLINE,
                                        's': suggestion.id,
                                    })))
    return markup


def create_post_votes_markup(poll_id):
    """
    Создает массив кнопок для опроса с количеством голосов

    :param poll_id: Идентификатор опроса
    :return: Массив кнопок
    :rtype list
    """
    poll = repo.get_poll(poll_id)
    if poll is None:
        raise Exception("Poll not found")
    buttons = list()
    option_votes = poll.get_votes_by_options()
    for poll_option in poll.options:
        # Создаем кнопку. В нагрузку сохраняем идентификаторы опроса и варианта ответа
        btn = InlineKeyboardButton("%s %d" % (poll_option.text, len(option_votes[poll_option.id])),
                                   callback_data=json.dumps({
                                       "a": ACTION_VOTE,
                                       "p": poll.id,
                                       "o": poll_option.id
                                   }))
        buttons.append(btn)
    poll_markup = InlineKeyboardMarkup(row_width=len(buttons))
    poll_markup.add(*buttons)
    return poll_markup


def rerender_post_votes(poll_id):
    """
    Обновляет кнопки голосования у поста

    :param poll_id: Идентификатор поста в канале
    :return:
    """
    poll = repo.get_poll(poll_id)
    if poll is None:
        raise Exception("Poll not found")
    poll_markup = create_post_votes_markup(poll_id)
    bot.edit_message_reply_markup(config.APP_CHANNEL_ID,
                                  poll.message_id,
                                  reply_markup=poll_markup)


def answer_callback_decision(call: CallbackQuery, decision: str):
    """
    Отвечает на сообщение-колбек клика по кнопке админу

    Отправляется при нажатии по кнопке Запостить и Отклонить.

    :param call:
    :param decision: Решение
    """
    if decision == DECISION_DECLINE:
        resolution_text = t("app.admin.decision.declined.plain")
    elif decision == DECISION_ACCEPT:
        resolution_text = t("app.admin.decision.accepted.plain")
    elif decision == DECISION_ACCEPT_WITH_POLL:
        resolution_text = t("app.admin.decision.accepted_with_poll.callback_answer")
    else:
        raise Exception("Ошибка выбора решения")
    bot.answer_callback_query(call.id, resolution_text)


def publish_post(file_id: str, reply_markup: InlineKeyboardMarkup = None) -> TelebotMessage:
    """
    Публикует пост в канале

    :param file_id: Идентификатор файла
    :param reply_markup: Кнопки опроса или None если не нужны
    :return: Пост
    """
    me = bot.get_me()
    channel_post = bot.send_photo(config.APP_CHANNEL_ID,
                                  file_id,
                                  caption=t("app.bot.sign",
                                            bot_username=me.username),
                                  parse_mode="HTML",
                                  reply_markup=reply_markup)
    return channel_post


def notify_user_about_publish(suggestion: Suggestion):
    """
    Отправляет пользователю уведомление о том, что его предложка опубликована

    :param suggestion:
    :return:
    """
    # Выключаем превью ссылок, чтобы не прикрепилось превью поста
    post_url = generate_post_link(suggestion.channel_post_id)
    bot.send_message(suggestion.user_id,
                     t("app.bot.user.published",
                       post_url=post_url),
                     reply_to_message_id=suggestion.user_message_id,
                     parse_mode="HTML",
                     disable_web_page_preview=True)


@bot.message_handler(commands=["start", "help"])
def send_help(message: TelebotMessage):
    """
    Отправка помощи. Отправляется на команды `\\\\start` и `\\\\help`
    """
    channel = get_channel()
    bot.send_message(message.chat.id,
                     t("app.bot.message.start",
                       channel_title=channel.title,
                       channel_username=channel.username),
                     parse_mode="HTML")


@bot.message_handler(commands=['cancel'])
@db.commit_session
def catch_cancel_command(message: TelebotMessage, session=None):
    """
    Обработка команды Отмена (`\\\\cancel`)

    Сценарии:
     1) Бот ждет от админа список эмодзи для опроса - Отменяем состояние
     и возвращаем предложке кнопки выбора решения

    """
    admin_id = get_admin_id()
    # Принимаем команду только в чате админа
    if message.chat.id != admin_id:
        return
    admin_state = repo.get_admin_state()
    # Если состояние чата админа пустое, ничего не делаем
    if admin_state is None:
        return
    # Если состояние чата - ожидает кнопки, то отменяем это состояние
    # и возвращаем предложке кнопки выбора решения
    if admin_state['state'] == AdminState.STATE_WAIT_BUTTONS:
        suggestion = repo.get_suggestion(admin_state['data']['suggestion_id'])
        if suggestion is None:
            raise Exception("Suggestion not found")
        repo.clear_admin_state()
        reset_suggestion(suggestion)
        # Отправляем сообщение, что операция отменена и удаляем клавиатуру, если есть
        bot.send_message(admin_id, t("app.bot.admin.cancel"), reply_markup=ReplyKeyboardRemove())


@bot.message_handler(content_types=['text'])
@db.commit_session
def catch_text_message(message: TelebotMessage, session=None):
    admin_id = get_admin_id()
    if message.chat.id != admin_id:
        bot.send_message(message.chat.id, t("app.bot.user.wrong_content"))
    admin_state = repo.get_admin_state()
    if admin_state is None:
        # Когда админ в пустом состоянии считаем его обычным пользователем
        bot.send_message(message.chat.id, t("app.bot.user.wrong_content"))
        return
    if admin_state['state'] == AdminState.STATE_WAIT_BUTTONS:
        suggestion = repo.get_suggestion(admin_state['data']['suggestion_id'])
        if suggestion is None:
            raise Exception("Suggestion not found")
        # Находим эмодзи в тексте
        emoji_chars = utils.find_emoji_in_text(message.text)
        # Не было найдено ниодного или более 6 эмодзи
        if len(emoji_chars) > 6 or len(emoji_chars) == 0:
            bot.send_message(message.chat.id,
                             t("app.bot.admin.error.poll.emoji_restrictions"))
            return
        # Создаем опрос в БД
        poll = repo.create_poll(emoji_chars)
        poll_markup = create_post_votes_markup(poll.id)
        # Публикуем пост
        channel_post = publish_post(suggestion.file_id, poll_markup)
        # Записываем в опрос идентификатор сообщения в канале
        poll.message_id = channel_post.message_id
        # Очищаем состояние админа
        repo.clear_admin_state()
        # Отправляем админу отбивку, что пост опубликован + очищаем клавиатуру (предложенные наборы эмодзи)
        bot.send_message(admin_id,
                         t("app.bot.admin.poll_posted"),
                         reply_to_message_id=suggestion.admin_message_id,
                         reply_markup=ReplyKeyboardRemove())
        # Обновляем предложку
        suggestion.decision = DECISION_ACCEPT_WITH_POLL
        suggestion.channel_post_id = channel_post.message_id
        rerender_suggestion(suggestion)
        # Отправляем пользователю информацию, что пост опубликован
        notify_user_about_publish(suggestion)
        # После вынесения решения удаляем предложку из базы
        session.delete(suggestion)


@bot.message_handler(content_types=['photo'])
@db.commit_session
def catch_photo(message: TelebotMessage, session=None):
    # Проверяем, что сообщение содержит изображение
    if len(message.photo) == 0:
        bot.send_message(message.chat.id, t("app.bot.user.wrong_content"))
        return
    # Создаем новую предложку
    suggestion = Suggestion()
    suggestion.state = Suggestion.STATE_NEW
    # Используем последнее фото с конца (наибольшее разрешение)
    suggestion.file_id = message.photo[-1].file_id
    # Сохраняем отправителя
    suggestion.user_title = get_full_name(message.from_user)
    suggestion.user_id = message.from_user.id
    suggestion.user_username = message.from_user.username
    # Сохраняем идентификатор сообщения в чате пользователя с ботом - понадобится чтобы бот
    # реплайнул на сообщение если его опубликуют
    suggestion.user_message_id = message.message_id
    # Проверяем, пользователь создал сообщение сам или переслал его
    if message.forward_from is not None or message.forward_from_chat is not None:
        if message.forward_from_chat is None:
            # Переслано от пользователя
            suggestion.forwarded_from_id = message.forward_from.id
            suggestion.forwarded_from_username = message.forward_from.username
            suggestion.forwarded_from_title = get_full_name(message.forward_from)
        else:
            # Переслано из канала
            suggestion.forwarded_from_id = message.forward_from_chat.id
            suggestion.forwarded_from_username = message.forward_from_chat.username
            suggestion.forwarded_from_title = message.forward_from_chat.title
    # Сохраняем предложку в базе
    session.add(suggestion)
    session.flush()
    # Создаем текст и кнопки для предложки
    admin_message = render_suggestion_text(suggestion)
    markup = create_admin_reply_markup(suggestion)
    # Отправляем предложку админу
    suggestion_message = bot.send_photo(config.APP_BOT_ADMIN_ID,
                                        suggestion.file_id,
                                        admin_message,
                                        reply_markup=markup,
                                        parse_mode="HTML")
    # Сохраняем идентификатор сообщения с предложкой
    suggestion.admin_message_id = suggestion_message.message_id
    # Отправляем пользователю сообщение о том, что его предложка отправлена
    bot.send_message(message.chat.id, t("app.bot.user.posted"))


@bot.message_handler(func=lambda message: True, content_types=None)
def catch_any_message(message: TelebotMessage):
    """
    Сообщение на случай, если отправлен неподдерживаемый контент

    :param message:
    """
    bot.send_message(message.chat.id, t("app.bot.user.wrong_content"))


def call_is_on_admin_suggestion(call: CallbackQuery):
    callback_data = json.loads(call.data)
    callback_action = callback_data['a']
    return callback_action in ADMIN_SUGGESTION_ACTIONS


def call_is_on_vote(call: CallbackQuery):
    callback_data = json.loads(call.data)
    callback_action = callback_data['a']
    return callback_action in VOTE_ACTIONS


@bot.callback_query_handler(func=call_is_on_admin_suggestion)
@db.commit_session
def call_on_admin_suggestion(call: CallbackQuery, session=None):
    """
    Обработка действий нажатия на кнопки предложки у админа

    :param call:
    :param session:
    """
    callback_data = json.loads(call.data)
    callback_action = callback_data['a']
    if callback_action == ACTION_DECLINE:
        callback_suggestion_id = callback_data['s']
        suggestion = repo.get_suggestion(callback_suggestion_id)
        if suggestion is None:
            raise Exception("Suggestion not found")
        if not suggestion.is_new():
            # Для это действия предложка должна быть только что опубликованной
            bot.answer_callback_query(call.id, t("bot.admin.error.decision.wrong_state"))
            return
        # Обновляем сообщение предложки и удаляем кнопки
        suggestion.decision = DECISION_DECLINE
        rerender_suggestion(suggestion)
        # Отображаем плашку с отменой
        answer_callback_decision(call, DECISION_DECLINE)
        # После вынесения решения удаляем предложку из базы
        session.delete(suggestion)
        return
    elif callback_action == ACTION_ACCEPT:
        callback_suggestion_id = callback_data['s']
        suggestion = repo.get_suggestion(callback_suggestion_id)
        if suggestion is None:
            raise Exception("Suggestion not found")
        if not suggestion.is_new():
            # Для это действия предложка должна быть только что опубликованной
            return
        # Отображаем плашку с ответом
        answer_callback_decision(call, DECISION_ACCEPT)
        # Публикуем пост в канале
        channel_post = publish_post(suggestion.file_id)
        # Обновляем предложку
        suggestion.decision = DECISION_ACCEPT
        suggestion.channel_post_id = channel_post.message_id
        # Обновляем сообщение предложки и удаляем кнопки
        rerender_suggestion(suggestion)
        # Отправляем пользователю информацию, что пост одобрен
        notify_user_about_publish(suggestion)
        # После вынесения решения удаляем предложку из базы
        session.delete(suggestion)
    elif callback_action == ACTION_ACCEPT_WITH_POLL:
        callback_suggestion_id = callback_data['s']
        suggestion = repo.get_suggestion(callback_suggestion_id)
        if suggestion is None:
            raise Exception("Suggestion not found")
        # Сохраняем состояние чата админа с ботом
        admin_state = repo.get_admin_state()
        if admin_state is not None and admin_state['state'] == AdminState.STATE_WAIT_BUTTONS:
            # Если другое сообщение уже ожидает эмодзи от пользователя, то возобновляем
            # кнопки в том сообщении
            other_suggestion = repo.get_suggestion(admin_state['data']['suggestion_id'])
            if other_suggestion is None:
                raise Exception("Suggestion not found")
            reset_suggestion(other_suggestion)
            admin_id = get_admin_id()
            # Отправляем сообщение о том, что предыдущая операция отменена + удаляем кнопки если есть
            # TODO попробовать совместить с /cancel
            bot.send_message(admin_id,
                             t("app.bot.admin.previous_action_canceled"),
                             reply_to_message_id=other_suggestion.admin_message_id,
                             reply_markup=ReplyKeyboardRemove())
        repo.set_admin_state(AdminState.STATE_WAIT_BUTTONS, {"suggestion_id": suggestion.id})
        # Показываем плашку о том, что решение принято
        answer_callback_decision(call, DECISION_ACCEPT_WITH_POLL)
        # Удаляем кнопки
        rerender_suggestion(suggestion)
        # Отправляем сообщение о том, что ждем эмодзи
        suggested_emoji_set_markup = ReplyKeyboardMarkup()
        previous_emoji_sets = repo.get_previous_emoji_sets()
        for emoji_set in previous_emoji_sets:
            suggested_emoji_set_markup.add(KeyboardButton(emoji_set))
        bot.send_message(call.message.chat.id,
                         t("app.bot.admin.wait_buttons"),
                         reply_to_message_id=suggestion.admin_message_id,
                         reply_markup=suggested_emoji_set_markup if len(previous_emoji_sets) > 0 else None)
        suggestion.state = Suggestion.STATE_WAIT
        # TODO прикрепить к сообщению последние 5 вариантов (не присылать при этом дубли)


@bot.callback_query_handler(func=call_is_on_vote)
@db.commit_session
def callback_handler(call: CallbackQuery, session=None):
    """
    Обработка нажатий на кнопках опроса

    :param call:
    :param session:
    """
    callback_data = json.loads(call.data)
    callback_action = callback_data['a']
    if callback_action == ACTION_VOTE:
        # Сценарии голосования:
        # 1) Первое нажание на кнопку любую кнопку - добавляем голос
        # 2) Повтороное нажание на кнопку, по которой уже отдан голос - снимаем голос
        # 3) Нажание на другую кнопку, отличную от той по которой отдан лолос - снимаем голос, добавляем новый
        user_id = call.from_user.id
        callback_poll_id = callback_data['p']
        callback_option_id = callback_data['o']
        option = repo.get_option(callback_option_id)
        if option is None:
            # Ошибка: вариант ответа опроса не найден
            bot.answer_callback_query(call.id, t("app.poll.vote.error"))
            return
        vote = repo.get_vote(callback_poll_id, user_id)
        poll = option.poll
        if vote is None:
            # Пользователь сделал первый голос
            repo.add_vote(poll.id, callback_option_id, user_id)
            bot.answer_callback_query(call.id, t("app.poll.vote.voted", emoji=option.text))
            rerender_post_votes(poll.id)
            return
        elif vote.option.id == option.id:
            # Пользователь повторно нажал на кнопку - голос отменен
            repo.clear_vote(poll.id, user_id)
            bot.answer_callback_query(call.id, t("app.poll.vote.canceled", emoji=option.text))
            rerender_post_votes(poll.id)
            return
        elif vote.option.id != option.id:
            # Пользователь проголосовал за другой вариант
            repo.clear_vote(poll.id, user_id)
            repo.add_vote(poll.id, option.id, user_id)
            bot.answer_callback_query(call.id, t("app.poll.vote.voted", emoji=option.text))
            rerender_post_votes(poll.id)
            return
        else:
            # Ошибка: что-то пошло не так
            bot.answer_callback_query(call.id, t("app.poll.vote.error"))
            return
        pass
