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

_time_offset_cache = None

@dataclass(frozen=True)
class CurrentTimeInfo:
    day_name: str
    date_str_display: str  
    date_str_iso: str  
    time_obj: time

def get_current_day_and_time() -> CurrentTimeInfo:
    global _time_offset_cache

    if _time_offset_cache is None:
        try:
            # Жестко ограничиваем таймаут (1 сек на коннект, 1 сек на чтение)
            response = requests.head("https://yandex.com/time/sync.json", timeout=(1.0, 1.0))
            response.raise_for_status()
            gmt_time_str = response.headers.get('Date')
            if not gmt_time_str: raise ValueError("Header 'Date' is missing")
            gmt_datetime = datetime.strptime(gmt_time_str, '%a, %d %b %Y %H:%M:%S GMT')
            
            _time_offset_cache = gmt_datetime - datetime.utcnow()
            log.info("Время успешно синхронизировано с Яндексом.")
        except Exception as e:
            log.warning("Сеть недоступна или заблокирована. Переход на локальное системное время.")
            _time_offset_cache = "USE_SYSTEM_TIME"

    # Если Яндекса нет, берем время с твоего Windows (или сервера)
    if _time_offset_cache == "USE_SYSTEM_TIME":
        local_datetime = datetime.now()
    else:
        local_datetime = datetime.utcnow() + _time_offset_cache + TIME_OFFSET

    day_name = DAYS_RU[local_datetime.weekday()]
    date_str_display = f"{local_datetime.day} {MONTHS_RU[local_datetime.month - 1]} {local_datetime.year} г."
    date_str_iso = local_datetime.strftime('%Y-%m-%d')
    current_time_obj = local_datetime.time()

    return CurrentTimeInfo(
        day_name=day_name,
        date_str_display=date_str_display,
        date_str_iso=date_str_iso,
        time_obj=current_time_obj
    )
