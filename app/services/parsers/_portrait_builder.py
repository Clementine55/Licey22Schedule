from typing import List, Dict, Any
from itertools import groupby
from .common_structs import RawLesson


def build_portrait_view(daily_lessons: List[RawLesson]) -> Dict[str, Any]:
    """
    Строит структуру данных для портретного режима из плоского списка уроков.
    """
    portrait_data = {}

    # Группируем все уроки по имени класса
    key_func = lambda lesson: lesson.class_name
    sorted_lessons = sorted(daily_lessons, key=key_func)

    for class_name, lessons_in_class_iter in groupby(sorted_lessons, key=key_func):
        lessons_list = list(lessons_in_class_iter)

        # Фильтруем пустые уроки и уроки без времени
        valid_lessons = [l for l in lessons_list if l.subject != '—' and l.start_time_obj]
        if not valid_lessons:
            continue

        portrait_data[class_name] = {
            'lessons': lessons_list,
            'first_lesson_time': min(l.start_time_obj for l in valid_lessons),
            'last_lesson_end_time': max(l.end_time_obj for l in valid_lessons if l.end_time_obj)
        }

    return portrait_data