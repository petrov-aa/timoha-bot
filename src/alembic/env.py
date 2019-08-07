import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# Импорт моделей приложения
# Меняем рабочую директорию чтобы был доступен импорт моделей
sys.path.append(os.getcwd())
from app import models
from app.env import ENV_VAR_DB_URL
target_metadata = models.Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    if ENV_VAR_DB_URL in os.environ:
        url = os.environ[ENV_VAR_DB_URL]
    else:
        url = "sqlite:///../data/db.db"
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    cfg = config.get_section(config.config_ini_section)
    # Используем либо URL базы из переменной окружения
    # или по умолчанию
    # Не используем URL к БД из модуля config чтобы от нас
    # не требовалось указание обязательных переменных окружения
    # вроде токена бота и т.д. для всего лишь операций с миграциями БД
    if ENV_VAR_DB_URL in os.environ:
        cfg["sqlalchemy.url"] = os.environ[ENV_VAR_DB_URL]
    else:
        cfg["sqlalchemy.url"] = "sqlite:///../data/db.db"
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
