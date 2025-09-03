import os
from dotenv import load_dotenv

# Определяем путь к файлу .env.
# Он ищет файл в той же директории, где находится config.py
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# --- Основные настройки приложения ---

class Config:
    """
    Класс для хранения конфигурационных переменных.
    Загружает переменные из окружения (из файла .env).
    """
    # Ваш OAuth-токен для API Яндекс.Диска
    # Получить его можно здесь: https://yandex.ru/dev/disk/poligon/
    YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')

    # Полный путь к файлу с расписанием на вашем Яндекс.Диске
    YANDEX_FILE_PATH = os.getenv('YANDEX_FILE_PATH')

    # Путь для сохранения скачанного файла.
    # Если переменная не задана в .env, используется значение по умолчанию.
    LOCAL_FILE_PATH = os.getenv('LOCAL_FILE_PATH', 'data/schedule.xlsx')

    #
    LOGO_FILE_PATH = os.getenv('LOGO_FILE_PATH', '/img/logo.png')

    # Время жизни кэша в секундах.
    CACHE_DURATION = int(os.getenv('CACHE_DURATION', 900))

    # Интервал автоматического пролистывания карусели (в секундах)
    CAROUSEL_INTERVAL = int(os.getenv('CAROUSEL_INTERVAL', 3))

    # Показывать расписание за X минут до начала первого урока
    SHOW_BEFORE_START_MIN = int(os.getenv('SHOW_BEFORE_START_MIN', 900))  # 1 час

    # Показывать расписание в течение X минут после окончания последнего урока
    SHOW_AFTER_END_MIN = int(os.getenv('SHOW_AFTER_END_MIN', 900))  # 30 минут

    # Выбор временного региона
    REGION_TIMEDELTA = int(os.getenv('REGION_TIMEDELTA', 7))  # +7 часов

    # Проверка, что переменные загрузились
    if not YANDEX_TOKEN or not YANDEX_FILE_PATH:
        raise ValueError("Необходимо задать YANDEX_TOKEN и YANDEX_FILE_PATH в файле .env")