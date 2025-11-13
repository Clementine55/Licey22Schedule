# app/services/clients/time_service.py

import requests
import logging
from datetime import datetime, timedelta, time
from config import Config
from dataclasses import dataclass


log = logging.getLogger(__name__)


DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
TIME_OFFSET = timedelta(hours=Config.REGION_TIMEDELTA)


@dataclass(frozen=True)
class CurrentTimeInfo:
    """Структура для хранения информации о текущем времени."""
    day_name: str
    date_str_display: str  # '17 октября 2025 г.' - для показа на экране
    date_str_iso: str  # '2025-10-17' - для сравнений и логики
    time_obj: time


def get_current_day_and_time() -> CurrentTimeInfo:
    """Определяет текущий день недели, дату и время."""
    try:
        response = requests.head("https://yandex.com/time/sync.json", timeout=5)
        response.raise_for_status()
        gmt_time_str = response.headers.get('Date')
        if not gmt_time_str: raise ValueError("Header 'Date' is missing")
        gmt_datetime = datetime.strptime(gmt_time_str, '%a, %d %b %Y %H:%M:%S GMT')
        local_datetime = gmt_datetime + TIME_OFFSET
        log.info("Время успешно получено от Яндекса.")
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        log.warning(f"Не удалось получить время от Яндекса ({e}). Используется системное время.")
        local_datetime = datetime.now()

    day_name = DAYS_RU[local_datetime.weekday()]
    date_str_display = f"{local_datetime.day} {MONTHS_RU[local_datetime.month - 1]} {local_datetime.year} г."
    date_str_iso = local_datetime.strftime('%Y-%m-%d')
    current_time_obj = local_datetime.time()

    log.info(f"Текущее время: {day_name}, {local_datetime.strftime('%H:%M:%S')}")

    return CurrentTimeInfo(
        day_name=day_name,
        date_str_display=date_str_display,
        date_str_iso=date_str_iso,
        time_obj=current_time_obj
    )