"""
Модуль операций с базой данных
"""

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.db import flush_session
from app.models import AdminState, Poll, PollOption, PollVote, Suggestion


def validate_admin_state(state: str, data: dict) -> bool:
    """
    Проверяет целостность состояния чата админа: проверка, что состоянию соответствует
    необходимый ему набор полей. Если состояние не проходит проверку на целостность, то
    возвращается `False`

    :param state:
    :param data:
    :return: Результат проверки состояния на целостность
    """
    if state == AdminState.STATE_WAIT_BUTTONS:
        # В состоянии "Ожидаю эмодзи для кнопок" в данных должен быть 1 ключ - идентификатор предложки
        if len(data.keys()) != 1:
            return False
        if "suggestion_id" not in data:
            return False
        return True
    else:
        return False


@flush_session
def sanitize_admin_state(session: Session = None):
    """
    Проверяет целостность хранения состояния в БД. В БД в каждый момент времени должно
    быть либо 0 строк - нет состояния, либо 1 строка - есть состояние.

    Если хранение состояния не целостно, то очищаем таблицу.

    Проверку выполняем перед каждой попыткой обращения к состоянию и после изменения.

    :param session:
    """
    states = session.query(AdminState).all()
    if len(states) > 1:
        for state in states:
            session.delete(state)


@flush_session
def get_admin_state(session: Session = None) -> Optional[dict]:
    """
    Возвращает состояние чата админа с ботом
    """
    sanitize_admin_state()
    admin_state = session.query(AdminState).first()
    if admin_state is None:
        return None
    if admin_state.state is None or admin_state.data is None:
        # Если одно из обязательных полей состояния не заполнено, считаем его невалидным и уничтожаем
        clear_admin_state()
        return None
    state = admin_state.state
    data = json.loads(admin_state.data)
    if not validate_admin_state(state, data):
        # Если объект состояния не проходит проверку на целостность, то уничтожаем состояние
        clear_admin_state()
        return None
    return {"state": admin_state.state, "data": json.loads(admin_state.data), "_raw": admin_state}


@flush_session
def set_admin_state(state: str, data: dict, session: Session = None):
    """
    Задает состояние чата админа с ботом
    """
    admin_state = get_admin_state()
    # Удаляем прошлое состояние если есть
    if admin_state is not None:
        clear_admin_state()
    admin_state = AdminState()
    admin_state.state = state
    admin_state.data = json.dumps(data)
    session.add(admin_state)
    session.flush()
    sanitize_admin_state()


@flush_session
def clear_admin_state(session: Session = None):
    """
    Очищает состояние чата админа с ботом
    """
    sanitize_admin_state()
    state = session.query(AdminState).first()
    session.delete(state)


@flush_session
def get_suggestion(suggestion_id: int, session: Session = None) -> Optional[Suggestion]:
    """
    Получить предложку по идентификатору в БД
    :param suggestion_id: Идентификатор предложки в БД
    :param session
    :return: Предложка
    """
    return session.query(Suggestion)\
        .filter(Suggestion.id == suggestion_id)\
        .first()


@flush_session
def create_poll(emojis: list, session: Session = None) -> Poll:
    """
    Создать опрос

    :param emojis: Массив эмодзи для вариантов ответа
    :param session:
    :return: Созданный опрос
    """
    poll = Poll()
    session.add(poll)
    for emoji in emojis:
        option = PollOption()
        option.poll = poll
        option.text = emoji
        session.add(option)
    return poll


@flush_session
def get_poll(poll_id: int, session: Session = None) -> Optional[Poll]:
    """
    Получить опрос по идентификатору

    :param poll_id: Идентификатор опроса
    :param session:
    :return: Опрос если найден или None
    """
    return session.query(Poll)\
        .filter(Poll.id == poll_id)\
        .first()


@flush_session
def get_option(option_id: int, session: Session = None) -> Optional[PollOption]:
    """
    Получить вариант ответа по идентификатору

    :param option_id: Идентификатор варианта ответа
    :param session:
    :return: Вариант ответа или None
    """
    return session.query(PollOption).filter(PollOption.id == option_id)\
        .first()


@flush_session
def get_vote(poll_id: int, user_id: int, session: Session = None) -> Optional[PollVote]:
    """
    Получить голос пользователя в опросе. Получаем массив голосов и оставляем только последний, а другие
    удаляем: могло получиться что пользователь быстро нажимал на кнопки или бот завис и сохранилось
    несколько голосов

    :param poll_id: Опрос
    :param user_id: Идентификатор пользователя в телеграме
    :param session:
    :return Голос
    """
    votes = session.query(PollVote)\
        .filter(PollVote.poll_id == poll_id,
                PollVote.user_id == user_id)\
        .all()
    votes_to_delete = votes[0:-1]
    votes = votes[-1:]
    # Удаляем ошибочно сохраненные мусорные голоса
    for vote_to_delete in votes_to_delete:
        session.delete(vote_to_delete)
    return votes[-1] if len(votes) == 1 else None


@flush_session
def clear_vote(poll_id: int, user_id: int, session: Session = None):
    """
    Удалить голос пользователя в опросе

    :param poll_id: Опрос
    :param user_id: Идентификатор пользователя в телеграме
    :param session:
    """
    vote = get_vote(poll_id, user_id)
    if vote is None:
        return
    session.delete(vote)


@flush_session
def add_vote(poll_id: int, option_id: int, user_id: int, session: Session = None):
    """
    Добавить голос пользователя в опрос

    :param poll_id: Опрос
    :param option_id: Вариант ответа
    :param user_id: Идентификатор пользователя в телеграме
    :param session:
    """
    vote = PollVote()
    vote.poll_id = poll_id
    vote.option_id = option_id
    vote.user_id = user_id
    session.add(vote)
