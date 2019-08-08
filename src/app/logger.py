import logging
from app import config

logger = logging.getLogger('app.logger')
__file_handler = logging.FileHandler(config.APP_LOG_FILENAME)
__formatter = logging.Formatter(
    '%(asctime)s (%(filename)s:%(lineno)d) %(levelname)s - %(name)s: "%(message)s"'
)
__file_handler.setFormatter(__formatter)

logger.setLevel(logging.ERROR)
logger.addHandler(__file_handler)
"""
Логгер приложения
"""
