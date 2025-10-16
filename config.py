import os
from dotenv import load_dotenv

# Определяем путь к файлу .env.
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """
    Класс для хранения конфигурационных переменных.
    Загружает переменные из окружения (из файла .env).
    """
    # Ваш OAuth-токен для API Яндекс.Диска
    YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')

    # --- НОВАЯ СТРУКТУРА ДЛЯ ХРАНЕНИЯ РАСПИСАНИЙ ---
    SCHEDULES = {}
    # Ищем в .env переменные, чтобы динамически собрать словарь расписаний
    i = 1
    while True:
        yandex_path = os.getenv(f'YANDEX_FILE_PATH_{i}')
        file_name_key = os.getenv(f'FILE_NAME_{i}')

        if not yandex_path or not file_name_key:
            break  # Прерываем цикл, если переменные для следующего номера не найдены

        local_path = f'data/{file_name_key}.xlsx'
        SCHEDULES[file_name_key] = {
            'yandex_path': yandex_path,
            'local_path': local_path
        }
        i += 1
    # --- КОНЕЦ НОВОЙ СТРУКТУРЫ ---

    LOGO_FILE_PATH = os.getenv('LOGO_FILE_PATH', 'img/logo.png')
    CACHE_DURATION = int(os.getenv('CACHE_DURATION', 900))
    CAROUSEL_INTERVAL = int(os.getenv('CAROUSEL_INTERVAL', 8))
    SHOW_BEFORE_START_MIN = int(os.getenv('SHOW_BEFORE_START_MIN', 60))
    SHOW_AFTER_END_MIN = int(os.getenv('SHOW_AFTER_END_MIN', 30))
    REGION_TIMEDELTA = int(os.getenv('REGION_TIMEDELTA', -7))

    # Проверка, что ключевые переменные загрузились
    if not YANDEX_TOKEN:
        raise ValueError("Необходимо задать YANDEX_TOKEN в файле .env")
    if not SCHEDULES:
        raise ValueError("Не найдено ни одной конфигурации расписания (YANDEX_FILE_PATH_1, FILE_NAME_1) в .env")