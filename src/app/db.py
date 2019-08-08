"""
Низкоуровневые взаимодействия с базой данных. Сессии
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app import config
from app.logger import logger as app_logger


__engine = create_engine(config.APP_DATABASE_URL, pool_pre_ping=True)

__SessionFactory = sessionmaker(bind=__engine)

__Session = scoped_session(__SessionFactory)


@contextmanager
def get_flush_session():
    session = __Session()
    try:
        yield session
        session.flush()
    except Exception as e:
        app_logger.error("Error during flush session: {}".format(str(e)))
        session.rollback()
        raise


def flush_session(func):
    """
    Декторатор для функций, в которых необходимо производить манипуляции с БД.
    Вызывает функци с дополнительным аргументом `session`, который можно использовать
    для запросов к БД. После окончания выполнения функции всегда вызвает `flush` сессии.

    :param func: Декорируемая функция
    :return:
    """
    def decorated(*args, **kwargs):
        with get_flush_session() as session:
            return func(*args, session=session, **kwargs)
    return decorated


@contextmanager
def get_commit_session():
    session = __Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        app_logger.error("Error during commit session: {}".format(str(e)))
        session.rollback()
    finally:
        session.close()
        __Session.remove()


def commit_session(func):
    """
    Декторатор для функций, в которых необходимо производить манипуляции с БД.
    Вызывает функци с дополнительным аргументом `session`, который можно использовать
    для запросов к БД. После окончания выполнения функции всегда вызвает `commit` сессии.
    Данный декторатор должен применяться у функций самого верхнего уровня, поскольку
    после окончания работы декорируемой функции сессия завершается.

    :param func:
    :return:
    """
    def decorated(*args, **kwargs):
        with get_commit_session() as session:
            return func(*args, **kwargs, session=session)
    return decorated
