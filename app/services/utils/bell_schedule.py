# app/services/bell_schedule.py (Финальная, исправленная версия с обратной совместимостью)

from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class Lesson:
    """Представляет один урок с номером, временем начала и окончания."""
    number: int
    start_time: str
    end_time: str

BELLS: Dict[str, Dict[str, List[Lesson]]] = {
    "Обычный день": {
        "1 смена": [
            Lesson(number=1, start_time="8:30", end_time="9:10"),
            Lesson(number=2, start_time="9:15", end_time="9:55"),
            Lesson(number=3, start_time="10:05", end_time="10:45"),
            Lesson(number=4, start_time="10:55", end_time="11:35"),
            Lesson(number=5, start_time="11:45", end_time="12:25"),
            Lesson(number=6, start_time="12:35", end_time="13:15"),
            Lesson(number=7, start_time="13:25", end_time="14:05"),
            Lesson(number=8, start_time="14:15", end_time="14:55"),
            Lesson(number=9, start_time="15:05", end_time="15:45"),
            Lesson(number=10, start_time="15:55", end_time="16:35")
        ],
        "2 смена": [
            Lesson(number=0, start_time="12:35", end_time="13:15"),
            Lesson(number=1, start_time="13:25", end_time="14:05"),
            Lesson(number=2, start_time="14:15", end_time="14:55"),
            Lesson(number=3, start_time="15:05", end_time="15:45"),
            Lesson(number=4, start_time="15:55", end_time="16:35"),
            Lesson(number=5, start_time="16:40", end_time="17:20"),
            Lesson(number=6, start_time="17:25", end_time="18:05"),
            Lesson(number=7, start_time="18:10", end_time="18:50"),
        ]
    },
    "Короткий день": {
        "1 смена": [
            Lesson(number=1, start_time="8:30", end_time="9:00"),
            Lesson(number=2, start_time="9:05", end_time="9:35"),
            Lesson(number=3, start_time="9:45", end_time="10:15"),
            Lesson(number=4, start_time="10:25", end_time="10:55"),
            Lesson(number=5, start_time="11:05", end_time="11:35"),
            Lesson(number=6, start_time="11:40", end_time="12:10"),
            Lesson(number=7, start_time="12:15", end_time="12:45"),
            Lesson(number=8, start_time="12:55", end_time="13:25"),
            Lesson(number=9, start_time="13:35", end_time="14:05"),
            Lesson(number=10, start_time="14:15", end_time="14:45")
        ],
        "2 смена": [
            Lesson(number=0, start_time="11:05", end_time="11:35"),
            Lesson(number=1, start_time="11:40", end_time="12:10"),
            Lesson(number=2, start_time="12:15", end_time="12:45"),
            Lesson(number=3, start_time="12:55", end_time="13:25"),
            Lesson(number=4, start_time="13:35", end_time="14:05"),
            Lesson(number=5, start_time="14:15", end_time="14:45"),
            Lesson(number=6, start_time="14:50", end_time="15:20"),
            Lesson(number=7, start_time="15:25", end_time="15:55")
        ]
    }
}


def get_lesson_by_number(lesson_number: any, shift: str, day_type: str = "Обычный день") -> Optional[Lesson]:
    """
    Основная функция для парсера расписания.
    Возвращает объект Lesson по его порядковому номеру.
    """
    try:
        num = int(float(lesson_number))
    except (ValueError, TypeError):
        return None

    schedule = BELLS.get(day_type, {}).get(shift)
    if not schedule:
        return None

    for lesson in schedule:
        if lesson.number == num:
            return lesson

    return None

# --- ИСПРАВЛЕНИЕ: ВОЗВРАЩАЕМ ЭТУ ФУНКЦИЮ НАЗАД ---
def get_end_time(start_time: str, shift: str, day_type: str = "Обычный день") -> Optional[str]:
    """
    Восстановлена для обратной совместимости с парсером консультаций.
    Находит время окончания по времени начала.
    """
    schedule = BELLS.get(day_type, {}).get(shift)
    if not schedule:
        return None

    # Ищем урок с таким же временем начала
    for lesson in schedule:
        if lesson.start_time == start_time:
            return lesson.end_time

    return None