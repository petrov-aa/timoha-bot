#!/bin/sh

if [ ! -z $X_SECRET_FILE ]; then
    export SECRET=$(cat $X_SECRET_FILE)
fi

# Ждем старта mysql
sleep 10

# Производим миграции
alembic upgrade head
# Запускаем приложение
python bot.py
