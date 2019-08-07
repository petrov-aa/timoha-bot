from sqlalchemy import Column, Integer, ForeignKey, String, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Suggestion(Base):
    """
    Предложка.

    Смысл таблицы в том, чтобы она являлась временным представлением предложки от момента предложения,
    до вынесения решения. Она используется для того, чтобы редактировать предложку в чате админа
    с ботом. На каждом этапе жизненного цикла предложки требуется наличие разных данных, которые
    должны однозначно определять то, как должно рендериться сообщение предложки в чате админа.
    Алтернативой этой таблице было бы хранить данные о предложки внутри нагрузки кнопок и в состоянии
    админа, что неэффективно и неоднородно, накладывает дополнительные усилия к написанию кода, затрудняет
    переиспользование кода.
    """
    __tablename__ = "suggestion"

    id = Column(Integer, primary_key=True)
    state = Column(String(30))
    # Отправитель
    user_id = Column(String(255))
    user_username = Column(String(255))
    user_title = Column(String(255))
    # Текст, добавленный отправителем
    text = Column(String(255))
    # Идентификатор файла
    file_id = Column(String(255))
    # Идентификатор сообщения в чате отправителя с ботом
    user_message_id = Column(Integer)
    # Переслано от
    forwarded_from_id = Column(String(255))
    forwarded_from_username = Column(String(255))
    forwarded_from_title = Column(String(255))
    # Идентификатор предложки в чате админа с ботом
    admin_message_id = Column(Integer)
    # Решение
    decision = Column(String(30))
    # Идентификатор поста в канале
    channel_post_id = Column(Integer)

    STATE_NEW = "new"
    """
    Предложку только отправили
    """
    STATE_WAIT = "wait"
    """
    Предложка ожидает данных от админа
    """
    STATE_PUBLISHED = "published"
    """
    Предложка опубликована
    """

    def user_is_public(self) -> bool:
        """
        Отправитель публичен (имеет юзернейм)
        :return:
        """
        return self.user_username is not None

    def is_forward(self) -> bool:
        """
        Предложка является пересланным сообщением
        :return:
        """
        return self.forwarded_from_title is not None

    def forwarded_is_public(self) -> bool:
        """
        Автор пересланного сообщения публичен (имеет юзернейм)
        :return:
        """
        return self.forwarded_from_username is not None

    def is_new(self) -> bool:
        return self.state == self.STATE_NEW

    def reset_to_new(self):
        """
        Восстанавливает состояние предложки в новое
        """
        self.state = self.STATE_NEW
        self.decision = None
        self.channel_post_id = None


class Poll(Base):
    """
    Опрос
    """
    __tablename__ = "poll"

    id = Column(Integer, primary_key=True)
    # Идентификатор сообщения c опросом в телеграме
    message_id = Column(String(255))
    options = relationship("PollOption", cascade="all, delete-orphan")
    votes = relationship("PollVote", cascade="all, delete-orphan")

    def get_unique_votes(self):
        """
        Возвращем только последние голоса пользователя

        :return:
        """
        unique = dict()
        for vote in self.votes:
            unique[vote.user_id] = vote
        vts = list(unique.values())
        return vts

    def get_votes_by_options(self):
        """
        Получаем словарь голосов по вариантам ответа
        :return:
        """
        unique_votes = self.get_unique_votes()
        result = dict()
        for option in self.options:
            result[option.id] = list()
        for vote in unique_votes:
            result[vote.option_id].append(vote)
        return result


class PollOption(Base):
    """
    Вариат ответа опроса
    """
    __tablename__ = "poll_option"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("poll.id", ondelete="CASCADE"))
    poll = relationship("Poll")
    # Текст кнопки-ответа (должен быть эмодзи)
    text = Column(String(4))
    votes = relationship("PollVote", cascade="all, delete-orphan")


class PollVote(Base):
    """
    Результаты голосования
    """
    __tablename__ = "poll_vote"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("poll.id", ondelete="CASCADE"))
    poll = relationship("Poll")
    option_id = Column(Integer, ForeignKey("poll_option.id", ondelete="CASCADE"))
    option = relationship("PollOption")
    # Идентификатор пользователя телеграм оставившего голос
    user_id = Column(Integer)


class AdminState(Base):
    """
    Информация о состоянии чата бота с админом: нужна для фичи создания опросов
    """
    __tablename__ = "admin_state"

    id = Column(Integer, primary_key=True)
    # Состояние
    state = Column(String(255))
    # Связанные с состоянием данные
    data = Column(Text)

    STATE_WAIT_BUTTONS = "wait_buttons"
    """
    Ожидаю эмодзи для кнопок - Бот ожидает пока админ пришлет кнопки
    """

