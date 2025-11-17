# app/services/parsers/landscape_builder.py

import re
from itertools import groupby
from datetime import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .common_structs import RawLesson

from app.services.utils.enums import Shift


# --- Структуры данных, специфичные для ландшафтного режима ---
@dataclass
class LandscapeTableRow:
    lesson_number: any
    display_time: str
    subjects: Dict[str, Dict[str, str]] = field(default_factory=dict)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass
class LandscapeGradeGroup:
    grade_key: str
    class_names: List[str]
    schedule_rows: List[LandscapeTableRow]
    first_lesson_time: time
    last_lesson_end_time: time


# --- Вспомогательная функция, перенесенная из старого парсера ---
def _process_grade_group(grade_classes: Dict[str, List[RawLesson]], grade_num: int, shift: Shift,
                         part_info: str = "") -> Optional[LandscapeGradeGroup]:
    grade_class_names = sorted(grade_classes.keys())
    all_lessons = [lesson for lessons in grade_classes.values() for lesson in lessons if lesson.subject != '—']
    valid_lessons = [l for l in all_lessons if l.start_time_obj]
    if not valid_lessons: return None

    last_lesson_end_time_obj = max(l.end_time_obj for l in valid_lessons if l.end_time_obj)

    schedule_rows = []
    key_func = lambda l: l.display_time
    sorted_lessons = sorted(all_lessons, key=lambda l: l.start_time_obj or time(0, 0))

    for display_time, lessons_in_group_iter in groupby(sorted_lessons, key=key_func):
        lessons_in_group = list(lessons_in_group_iter)
        first_lesson = lessons_in_group[0]
        subjects_for_row = {}
        for class_name in grade_class_names:
            lesson = next((l for l in lessons_in_group if l.class_name == class_name), None)
            subjects_for_row[class_name] = {'предмет': lesson.subject, 'кабинет': lesson.cabinet} if lesson else {
                'предмет': '', 'кабинет': ''}

        schedule_rows.append(LandscapeTableRow(
            lesson_number=first_lesson.lesson_number, display_time=display_time,
            subjects=subjects_for_row, start_time=first_lesson.start_time, end_time=first_lesson.end_time
        ))

    return LandscapeGradeGroup(
        grade_key=f"{grade_num}-е классы ({shift.value}){part_info}",
        class_names=grade_class_names, schedule_rows=schedule_rows,
        first_lesson_time=min(l.start_time_obj for l in valid_lessons),
        last_lesson_end_time=last_lesson_end_time_obj
    )


# --- Главная функция "строителя" ---
def build_landscape_view(daily_lessons: List[RawLesson]) -> List[List[Dict[str, Any]]]:
    """
    Строит структуру данных для ландшафтного режима (слайды карусели).
    """
    temp_landscape_view = {}

    # Группируем уроки по сменам
    sort_key = lambda l: l.shift.name
    group_key = lambda l: l.shift

    sorted_by_shift = sorted(daily_lessons, key=sort_key)

    for shift_obj, lessons_in_shift_iter in groupby(sorted_by_shift, key=group_key):
        # Теперь shift_obj - это Shift.FIRST или Shift.SECOND
        lessons_in_shift = list(lessons_in_shift_iter)

        # Группируем уроки в смене по классам (10, 11 и т.д.)
        get_grade = lambda l: int(re.match(r'(\d+)', l.class_name).group(1))
        for grade_num, lessons_in_grade_iter in groupby(sorted(lessons_in_shift, key=get_grade), key=get_grade):
            if grade_num < 5: continue

            # Группируем по полному имени класса ('10А', '10Б')
            lessons_by_class_name = {
                k: list(v) for k, v in
                groupby(sorted(list(lessons_in_grade_iter), key=lambda l: l.class_name), key=lambda l: l.class_name)
            }

            num_classes = len(lessons_by_class_name)
            if num_classes <= 6:
                group = _process_grade_group(lessons_by_class_name, grade_num, shift_obj)
                if group: temp_landscape_view[group.grade_key] = group
            else:  # Разбиваем большие параллели на 2 части
                split_point = (num_classes + 1) // 2
                sorted_items = sorted(lessons_by_class_name.items())
                group1 = _process_grade_group(dict(sorted_items[:split_point]), grade_num, shift_obj, " (1/2)")
                if group1: temp_landscape_view[group1.grade_key] = group1
                group2 = _process_grade_group(dict(sorted_items[split_point:]), grade_num, shift_obj, " (2/2)")
                if group2: temp_landscape_view[group2.grade_key] = group2

    # Финальная группировка по слайдам (по 2 группы на слайд, если влезает)
    landscape_slides = []
    sorted_keys = sorted(temp_landscape_view.keys(), key=lambda k: (int(re.search(r'(\d+)', k).group(1)), k))
    i = 0
    while i < len(sorted_keys):
        g1_data = temp_landscape_view[sorted_keys[i]]
        if i + 1 < len(sorted_keys):
            g2_data = temp_landscape_view[sorted_keys[i + 1]]
            if len(g1_data.schedule_rows) + len(g2_data.schedule_rows) > 16:
                landscape_slides.append([g1_data])
                i += 1
            else:
                landscape_slides.append([g1_data, g2_data])
                i += 2
        else:
            landscape_slides.append([g1_data])
            i += 1

    return landscape_slides