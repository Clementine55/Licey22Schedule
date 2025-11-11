import pandas as pd
import logging
import re
from typing import List, Dict

# Импортируем наши новые и старые утилиты
from .common_structs import RawLesson
from ..utils.data_validator import is_valid_class_name, normalize_class_name, parse_time_str
from ..utils.bell_schedule import get_lesson_by_number

log = logging.getLogger(__name__)


# Вспомогательные функции, которые нужны именно этому парсеру
def _get_shift_from_time(time_str: str) -> str:
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


def parse_schedule(xls: pd.ExcelFile, day_type_override: str = None) -> Dict[str, List[RawLesson]]:
    """
    Главная функция парсера. Читает Excel и возвращает словарь, где
    ключ - это день недели, а значение - плоский список всех уроков за этот день.
    """

    raw_lessons_by_day: Dict[str, List[RawLesson]] = {}

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        required_columns = {'Дни', 'Уроки', 'Время'}
        if not required_columns.issubset(df.columns):
            continue

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
        sheet_shift_hint = _get_shift_from_sheet_name(sheet_name)

        for day_name, day_group in df.groupby('Дни'):
            if day_name not in raw_lessons_by_day:
                raw_lessons_by_day[day_name] = []

            master_day_grid = [{'урок': r['Уроки'], 'время': r['Время'], 'original_row': r} for _, r in
                               day_group.iterrows() if r['Уроки'] != '' and r['Время'] != '']
            if not master_day_grid: continue

            for class_name, (subject_col, cabinet_col) in class_column_pairs.items():
                if not any(str(info['original_row'][subject_col]).strip() for info in master_day_grid):
                    continue

                first_lesson_time = next(
                    (info['время'] for info in master_day_grid if str(info['original_row'][subject_col]).strip()),
                    "8:00")
                actual_shift = sheet_shift_hint or get_shift_from_time(first_lesson_time)

                for lesson_info in master_day_grid:
                    subject = str(lesson_info['original_row'][subject_col]).strip() or "—"
                    cabinet_raw = str(lesson_info['original_row'][cabinet_col]).strip()
                    cabinet = cabinet_raw[:-2] if cabinet_raw.endswith('.0') else cabinet_raw
                    lesson_number = lesson_info['урок']

                    bell_lesson = get_lesson_by_number(lesson_number, actual_shift, sheet_day_type)
                    start_t, end_t, display_t = None, None, str(lesson_info['время'])
                    if bell_lesson:
                        start_t, end_t = bell_lesson.start_time, bell_lesson.end_time
                        display_t = f"{start_t}–{end_t}"

                    raw_lesson = RawLesson(
                        day_name=day_name, class_name=class_name, shift=actual_shift,
                        lesson_number=lesson_number, display_time=display_t, subject=subject,
                        cabinet=cabinet, start_time=start_t, end_time=end_t,
                        start_time_obj=parse_time_str(start_t), end_time_obj=parse_time_str(end_t)
                    )
                    raw_lessons_by_day[day_name].append(raw_lesson)

    return raw_lessons_by_day