import requests
import logging
from datetime import datetime, timedelta
from config import Config

log = logging.getLogger(__name__)

DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
TIME_OFFSET = timedelta(hours=Config.REGION_TIMEDELTA)


def get_current_day_and_time():
    """
    Определяет текущий день недели, дату и время.
    :return: Кортеж (название_дня, отформатированная_дата, объект_времени)
    """
    try:
        response = requests.head("https://yandex.com/time/sync.json", timeout=5)
        response.raise_for_status()
        gmt_time_str = response.headers.get('Date')

        if not gmt_time_str:
            raise ValueError("Header 'Date' is missing")

        gmt_datetime = datetime.strptime(gmt_time_str, '%a, %d %b %Y %H:%M:%S GMT')
        local_datetime = gmt_datetime + TIME_OFFSET

        log.info("Время успешно получено от Яндекса.")

    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        log.warning(f"Не удалось получить время от Яндекса ({e}). Используется системное время.")
        local_datetime = datetime.now()

    day_name = DAYS_RU[local_datetime.weekday()]
    date_str = f"{local_datetime.day} {MONTHS_RU[local_datetime.month - 1]} {local_datetime.year} г."
    current_time_obj = local_datetime.time()
    log.info(f"Время: {day_name}, {local_datetime.strftime('%H:%M:%S')}")

    return day_name, date_str, current_time_obj

