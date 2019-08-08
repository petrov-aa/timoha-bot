"""
Имена переменных окружения, используемые приложением
"""

ENV_VAR_DB_URL = "APP_DATABASE_URL"
"""
Переменная окружения содержащая
URL-подключения к БД, который можно использовать с `SQLAlchemy`

**Необязательная**: Если не задана, то используется значение по умолчанию:
```sqlite:///../data/db.db```
"""

ENV_VAR_BOT_TOKEN = "APP_BOT_TOKEN"
"""
Переменная окружения содержащая токен бота

**Обязательная**: Если не задана, то бот не запускается
"""

ENV_VAR_BOT_ADMIN_ID = "APP_BOT_ADMIN_ID"
"""
Идентификатор админа - пользователь, которому пересылается предложка

**Обязательная**: Если не задана, то бот не запускается
"""

ENV_VAR_PROXY = "APP_BOT_PROXY"
"""
Переменная окружения содержащая прокси для бота

**Необязательная**: Если не задана, то прокси не используется
"""

ENV_VAR_CHANNEL_ID = "APP_CHANNEL_ID"
"""
Идентификатор канала. Может быть либо идентификатором, либо юзернеймом вида: `@username`

**Обазательная**: Если не задана, то бот не запускается
"""

ENV_VAR_APP_RUN_METHOD = "APP_RUN_METHOD"
"""
Способ запуска бота: pooling или webhook
"""

ENV_VAR_LOG_FILENAME = "APP_LOG_FILENAME"
"""
Путь к файлу-логу
"""
