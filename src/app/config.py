"""
Конфигурационные переменные приложения
"""

import os
from app.env import *

APP_DATABASE_URL = "sqlite:///../data/db.db"
"""
URL-подключения к БД, который можно использовать с SQLAlchemy
"""
if ENV_VAR_DB_URL in os.environ:
    APP_DATABASE_URL = os.environ[ENV_VAR_DB_URL]

if ENV_VAR_BOT_TOKEN not in os.environ:
    raise Exception("Не задан токен бота")
APP_BOT_TOKEN = os.environ[ENV_VAR_BOT_TOKEN]
"""
Токен бота
"""

if ENV_VAR_BOT_ADMIN_ID not in os.environ:
    raise Exception("Не задан идентификатор админа")
APP_BOT_ADMIN_ID = os.environ[ENV_VAR_BOT_ADMIN_ID]
"""
Идентификатор или юзернейм админа, которому пересылается предложка
"""

APP_BOT_PROXY = None
"""
Прокси для бота. Если `None`, то прокси не используется
"""
if ENV_VAR_PROXY in os.environ:
    APP_BOT_PROXY = os.environ[ENV_VAR_PROXY]

if ENV_VAR_CHANNEL_ID not in os.environ:
    raise Exception("Не задан идентификатор или юзернейм канала")
APP_CHANNEL_ID = os.environ[ENV_VAR_CHANNEL_ID]
"""
Идентификатор или юзернейм канала
"""

if ENV_VAR_APP_RUN_METHOD not in os.environ:
    raise Exception("Не задан способ запуска бота")
APP_RUN_METHOD = os.environ[ENV_VAR_APP_RUN_METHOD]
"""
Способ запуска бота: pooling или webhook
"""
