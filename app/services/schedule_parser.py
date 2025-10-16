# app/services/schedule_parser.py (Версия с использованием dataclass)

import pandas as pd
import logging
import re
from itertools import groupby
from datetime import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .data_validator import is_valid_class_name, normalize_class_name, parse_time_str
from .bell_schedule import get_lesson_by_number

log = logging.getLogger(__name__)


# ===================================================================
# === 1. ОПРЕДЕЛЯЕМ СТРУКТУРЫ ДАННЫХ (DATA CLASSES) ===
# ===================================================================

@dataclass
class Lesson:
    """Хранит полную информацию об одном уроке для одного класса."""
    lesson_number: any
    display_time: str
    subject: str = "—"
    cabinet: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_time_obj: Optional[time] = None
    end_time_obj: Optional[time] = None


@dataclass
class LandscapeTableRow:
    """Хранит данные для одной строки в таблице ландшафтного режима."""
    lesson_number: any
    display_time: str
    subjects: Dict[str, Dict[str, str]] = field(default_factory=dict)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass
class LandscapeGradeGroup:
    """Представляет одну "карточку" (таблицу) в ландшафтном режиме."""
    grade_key: str
    class_names: List[str]
    schedule_rows: List[LandscapeTableRow]
    first_lesson_time: time
    last_lesson_end_time: time


# ===================================================================
# === 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (без изменений) ===
# ===================================================================

def get_shift_from_time(time_str: str) -> str:
    try:
        hour_str = time_str.split('.')[0].split(':')[0]
        hour = int(re.match(r'(\d+)', hour_str).group(1))
        return "2 смена" if hour >= 12 else "1 смена"
    except (ValueError, IndexError, AttributeError):
        return "1 смена"


def _get_shift_from_sheet_name(sheet_name: str) -> str or None:
    clean_name = str(sheet_name).strip().lower()
    if re.search(r'\(1\s?смена\)', clean_name): return "1 смена"
    if re.search(r'\(2\s?смена\)', clean_name): return "2 смена"
    return None


def _get_day_type_from_sheet_name(sheet_name: str) -> str:
    clean_name = str(sheet_name).strip().lower()
    if re.search(r'\(короткий день\)', clean_name) or re.search(r'\(сокр\)', clean_name):
        return "Короткий день"
    return "Обычный день"


# ===================================================================
# === 3. ОБНОВЛЕННЫЕ ФУНКЦИИ ПАРСЕРА ===
# ===================================================================

def _process_grade_group(grade_classes: Dict[str, List[Lesson]], grade_num: int, shift_name: str, day_type: str,
                         part_info: str = "") -> Optional[LandscapeGradeGroup]:
    grade_class_names = sorted(grade_classes.keys())

    all_lessons = [lesson for lessons in grade_classes.values() for lesson in lessons if lesson.subject != '—']
    valid_lessons = [l for l in all_lessons if l.start_time_obj]
    if not valid_lessons:
        return None

    last_lesson_end_time_obj = max(l.end_time_obj for l in valid_lessons if l.end_time_obj)

    # Группируем уроки по времени для создания строк таблицы
    schedule_rows = []
    key_func = lambda l: l.display_time
    sorted_lessons = sorted(all_lessons, key=lambda l: l.start_time_obj or time(0, 0))

    for display_time, lessons_in_group_iter in groupby(sorted_lessons, key=key_func):
        lessons_in_group = list(lessons_in_group_iter)
        first_lesson = lessons_in_group[0]

        subjects_for_row = {}
        for class_name in grade_class_names:
            lesson = next(
                (l for l in lessons_in_group if class_name in grade_classes and l in grade_classes[class_name]), None)
            subjects_for_row[class_name] = {'предмет': lesson.subject, 'кабинет': lesson.cabinet} if lesson else {
                'предмет': '', 'кабинет': ''}

        schedule_rows.append(LandscapeTableRow(
            lesson_number=first_lesson.lesson_number,
            display_time=display_time,
            subjects=subjects_for_row,
            start_time=first_lesson.start_time,
            end_time=first_lesson.end_time
        ))

    return LandscapeGradeGroup(
        grade_key=f"{grade_num}-е классы ({shift_name}){part_info}",
        class_names=grade_class_names,
        schedule_rows=schedule_rows,
        first_lesson_time=min(l.start_time_obj for l in valid_lessons),
        last_lesson_end_time=last_lesson_end_time_obj
    )


def parse_schedule(file_path: str, day_type_override: str = None) -> Optional[Dict]:
    try:
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')
        raw_data = {}
        for sheet_name, df in xls_dict.items():
            required_columns = ['Дни', 'Уроки', 'Время']
            if not all(col in df.columns for col in required_columns): continue

            class_column_pairs = {}
            df_columns = list(df.columns)
            i = 0
            while i < len(df_columns) - 1:
                col_name = str(df_columns[i])
                if is_valid_class_name(col_name):
                    normalized_name = normalize_class_name(col_name)
                    class_column_pairs[normalized_name] = (col_name, df_columns[i + 1])
                    i += 2
                else:
                    i += 1
            if not class_column_pairs: continue

            df['Дни'] = df['Дни'].ffill()
            df = df.fillna('')
            sheet_day_type = day_type_override or _get_day_type_from_sheet_name(sheet_name)
            sheet_shift = _get_shift_from_sheet_name(sheet_name)
            log.info(f"Processing sheet: '{sheet_name}'. Shift: '{sheet_shift}', Day Type: '{sheet_day_type}'")

            for day_name, day_group in df.groupby('Дни'):
                if day_name not in raw_data: raw_data[day_name] = {"1 смена": {}, "2 смена": {}}

                master_day_grid = [{'урок': r['Уроки'], 'время': r['Время'], 'original_row': r} for _, r in
                                   day_group.iterrows() if r['Уроки'] != '' and r['Время'] != '']
                if not master_day_grid: continue

                for normalized_name, (subject_col, cabinet_col) in class_column_pairs.items():
                    if not any(str(info['original_row'][subject_col]).strip() for info in master_day_grid): continue

                    first_lesson_time = next(
                        (info['время'] for info in master_day_grid if str(info['original_row'][subject_col]).strip()),
                        "8:00")
                    actual_shift = sheet_shift or get_shift_from_time(first_lesson_time)

                    lessons = []
                    for lesson_info in master_day_grid:
                        subject = str(lesson_info['original_row'][subject_col]).strip()
                        cabinet_raw = str(lesson_info['original_row'][cabinet_col]).strip()
                        cabinet = cabinet_raw[:-2] if cabinet_raw.endswith('.0') else cabinet_raw

                        lesson_number = lesson_info['урок']
                        bell_schedule_lesson = get_lesson_by_number(lesson_number, actual_shift, sheet_day_type)

                        start_t, end_t, display_t = None, None, str(lesson_info['время'])
                        if bell_schedule_lesson:
                            start_t = bell_schedule_lesson.start_time
                            end_t = bell_schedule_lesson.end_time
                            display_t = f"{start_t}–{end_t}"

                        lessons.append(Lesson(
                            lesson_number=lesson_number,
                            display_time=display_t,
                            subject=subject or "—",
                            cabinet=cabinet or "",
                            start_time=start_t,
                            end_time=end_t,
                            start_time_obj=parse_time_str(start_t),
                            end_time_obj=parse_time_str(end_t),
                        ))
                    raw_data[day_name][actual_shift][normalized_name] = lessons

        final_schedule = {}
        days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        for day in days_order:
            if day not in raw_data:
                final_schedule[day] = None
                continue

            day_data = {"portrait_view": {}, "landscape_slides": []}
            all_classes_for_day = {**raw_data[day]["1 смена"], **raw_data[day]["2 смена"]}

            for class_name, lessons_list in all_classes_for_day.items():
                valid_lessons = [l for l in lessons_list if l.subject != '—' and l.start_time_obj]
                if not valid_lessons: continue

                day_data["portrait_view"][class_name] = {
                    'lessons': [l.__dict__ for l in lessons_list],  # Конвертируем обратно в dict для JSON-сериализации
                    'first_lesson_time': min(l.start_time_obj for l in valid_lessons),
                    'last_lesson_end_time': max(l.end_time_obj for l in valid_lessons if l.end_time_obj)
                }

            temp_landscape_view = {}
            for shift_name in ["1 смена", "2 смена"]:
                classes_in_shift = raw_data[day][shift_name]
                if not classes_in_shift: continue

                get_grade = lambda item: int(re.match(r'(\d+)', item[0]).group(1))
                for grade_num, grade_iter in groupby(sorted(classes_in_shift.items(), key=get_grade), key=get_grade):
                    if grade_num < 5: continue

                    all_classes_for_grade = dict(grade_iter)
                    num_classes = len(all_classes_for_grade)

                    if num_classes <= 6:
                        group = _process_grade_group(all_classes_for_grade, grade_num, shift_name, sheet_day_type)
                        if group: temp_landscape_view[group.grade_key] = group.__dict__  # Конвертируем в dict
                    else:
                        split_point = (num_classes + 1) // 2
                        sorted_items = sorted(all_classes_for_grade.items())

                        group1 = _process_grade_group(dict(sorted_items[:split_point]), grade_num, shift_name,
                                                      sheet_day_type, " (1/2)")
                        if group1: temp_landscape_view[group1.grade_key] = group1.__dict__

                        group2 = _process_grade_group(dict(sorted_items[split_point:]), grade_num, shift_name,
                                                      sheet_day_type, " (2/2)")
                        if group2: temp_landscape_view[group2.grade_key] = group2.__dict__

            sorted_keys = sorted(temp_landscape_view.keys(), key=lambda k: (int(re.search(r'(\d+)', k).group(1)), k))
            i = 0
            while i < len(sorted_keys):
                g1_data = temp_landscape_view[sorted_keys[i]]
                g1_rows = len(g1_data.get('schedule_rows', []))
                if i + 1 < len(sorted_keys):
                    g2_data = temp_landscape_view[sorted_keys[i + 1]]
                    g2_rows = len(g2_data.get('schedule_rows', []))
                    if g1_rows + g2_rows > 16:
                        day_data["landscape_slides"].append([g1_data]);
                        i += 1
                    else:
                        day_data["landscape_slides"].append([g1_data, g2_data]);
                        i += 2
                else:
                    day_data["landscape_slides"].append([g1_data]);
                    i += 1

            final_schedule[day] = day_data
        return final_schedule
    except Exception as e:
        log.critical(f"Critical error parsing schedule file '{file_path}': {e}", exc_info=True)
        return None