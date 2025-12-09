# app/services/parsers/schedule_parser.py

import pandas as pd
import logging
import re
from typing import List, Dict, Tuple, Optional

from .common_structs import RawLesson

from app.services.utils.data_validator import is_valid_class_name, normalize_class_name, parse_time_str
from app.services.utils.bell_schedule import get_lesson_by_number
from app.services.utils.enums import DayType, Shift


log = logging.getLogger(__name__)


# Вспомогательные функции, которые нужны именно этому парсеру
def _format_lesson_number(val: any) -> str:
    try:
        float_val = float(val)
        if float_val.is_integer():
            return str(int(float_val))
        return str(val)
    except (ValueError, TypeError):
        return str(val).split('.')[0]


def _get_shift_from_time(time_str: str) -> Shift:
    try:
        hour_str = time_str.split('.')[0].split(':')[0]
        hour = int(re.match(r'(\d+)', hour_str).group(1))
        return Shift.SECOND if hour >= 12 else Shift.FIRST
    except (ValueError, IndexError, AttributeError):
        return Shift.FIRST


def _get_shift_from_sheet_name(sheet_name: str) -> Optional[Shift]:
    clean_name = str(sheet_name).strip().lower()
    if re.search(r'\(1\s?смена\)', clean_name): return Shift.FIRST
    if re.search(r'\(2\s?смена\)', clean_name): return Shift.SECOND
    return None


def _get_day_type_from_sheet_name(sheet_name: str) -> DayType:
    clean_name = str(sheet_name).strip().lower()
    if re.search(r'\(сокр\)', clean_name):
        return DayType.SHORT
    return DayType.NORMAL


def _find_class_columns(df_columns: List[str]) -> Dict[str, Tuple[str, str]]:
    """Находит и сопоставляет колонки предметов и кабинетов для каждого класса."""
    class_column_pairs = {}
    i = 0
    while i < len(df_columns) - 1:
        col_name = str(df_columns[i])
        if is_valid_class_name(col_name):
            normalized_name = normalize_class_name(col_name)
            # Предполагаем, что следующая колонка - это кабинет
            class_column_pairs[normalized_name] = (col_name, df_columns[i + 1])
            i += 2  # Перескакиваем через две колонки (предмет и кабинет)
        else:
            i += 1
    return class_column_pairs


# --- Главная функция парсера ---

def parse_schedule(xls: pd.ExcelFile, day_type_override: Optional[DayType] = None) -> Dict[str, List[RawLesson]]:
    """
    Главная функция парсера. Читает Excel и возвращает словарь, где
    ключ - это день недели, а значение - плоский список всех уроков за этот день.
    """
    raw_lessons_by_day: Dict[str, List[RawLesson]] = {}
    required_columns = {'Дни', 'Уроки', 'Время'}

    log.info("Запуск парсера расписания...")
    for sheet_name in xls.sheet_names:
        # 1. Проверяем, подходит ли лист для парсинга
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if not required_columns.issubset(df.columns):
            log.info(
                f"  [✗] Пропуск листа '{sheet_name}': не найдены обязательные колонки ({', '.join(required_columns)}).")
            continue

        class_column_pairs = _find_class_columns(list(df.columns))
        if not class_column_pairs:
            log.info(f"  [✗] Пропуск листа '{sheet_name}': не найдено ни одной колонки с именем класса.")
            continue

        log.info(f"  [✓] Анализ листа '{sheet_name}'...")

        # 2. Подготовка данных
        df['Дни'] = df['Дни'].ffill()
        df = df.fillna('')
        sheet_day_type = day_type_override or _get_day_type_from_sheet_name(sheet_name)
        sheet_shift_hint = _get_shift_from_sheet_name(sheet_name)

        # 3. Парсинг по дням недели
        for day_name, day_group in df.groupby('Дни'):
            if day_name not in raw_lessons_by_day:
                raw_lessons_by_day[day_name] = []

            master_day_grid = [{'урок': r['Уроки'], 'время': r['Время'], 'original_row': r}
                               for _, r in day_group.iterrows() if r['Уроки'] != '' and r['Время'] != '']
            if not master_day_grid:
                continue

            # 4. Парсинг по классам
            for class_name, (subject_col, cabinet_col) in class_column_pairs.items():
                if not any(str(info['original_row'][subject_col]).strip() for info in master_day_grid):
                    continue  # Пропускаем класс, если у него нет уроков в этот день

                first_lesson_time = next(
                    (info['время'] for info in master_day_grid if str(info['original_row'][subject_col]).strip()),
                    "8:00")
                actual_shift = sheet_shift_hint or _get_shift_from_time(first_lesson_time)

                # 5. Создание объектов RawLesson
                for lesson_info in master_day_grid:
                    subject = str(lesson_info['original_row'][subject_col]).strip() or "—"
                    cabinet_raw = str(lesson_info['original_row'][cabinet_col]).strip()
                    cabinet = cabinet_raw[:-2] if cabinet_raw.endswith('.0') else cabinet_raw

                    bell_lesson = get_lesson_by_number(lesson_info['урок'], actual_shift, sheet_day_type)
                    start_t, end_t, display_t = None, None, str(lesson_info['время'])
                    if bell_lesson:
                        start_t, end_t = bell_lesson.start_time, bell_lesson.end_time
                        display_t = f"{start_t}–{end_t}"

                    raw_lessons_by_day[day_name].append(RawLesson(
                        day_name=day_name, class_name=class_name, shift=actual_shift,
                        lesson_number=_format_lesson_number(lesson_info['урок']), display_time=display_t, subject=subject,
                        cabinet=cabinet, start_time=start_t, end_time=end_t,
                        start_time_obj=parse_time_str(start_t), end_time_obj=parse_time_str(end_t)
                    ))

    log.info("Парсер расписания завершил работу.")
    return raw_lessons_by_day