# app/services/parsers/common_struct.py

from dataclasses import dataclass
from typing import Optional
from datetime import time


@dataclass
class RawLesson:
    """
    Универсальная структура для хранения "сырых" данных об одном уроке,
    извлеченных напрямую из ячейки Excel.
    """
    day_name: str
    class_name: str
    shift: str

    lesson_number: any
    display_time: str  # Время как оно написано в файле, "8.30-9.10"
    subject: str
    cabinet: str

    # Дополнительные поля, которые вычисляются при парсинге
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_time_obj: Optional[time] = None
    end_time_obj: Optional[time] = None