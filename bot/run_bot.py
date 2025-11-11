import asyncio
import logging
import sys
import os

# Добавляем корневую папку проекта в путь, чтобы можно было импортировать config и app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
# Путь к bot_service теперь локальный
from bot_service import main


log = logging.getLogger(__name__)

if __name__ == '__main__':
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_ADMIN_IDS:
        log.error("TELEGRAM_BOT_TOKEN и TELEGRAM_ADMIN_IDS должны быть установлены в .env")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())