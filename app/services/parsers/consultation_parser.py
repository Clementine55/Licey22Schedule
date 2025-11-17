# app/services/parsers/consultation_parser.py

import pandas as pd
import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List

from app.services.utils.data_validator import parse_time_str
from app.services.utils.bell_schedule import get_end_time
from app.services.utils.enums import DayType, Shift


log = logging.getLogger(__name__)


@dataclass
class Consultation:
    teacher: str
    time: str
    room: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None


# --- Вспомогательные функции (оставляем как есть, они работают) ---
def _parse_consultation_time_for_sort(time_str: str) -> tuple:
    if not isinstance(time_str, str): return (99, 99)
    parts = time_str.split(',')[0].strip().split('-')[0].strip().replace('.', ':').split(':')
    if len(parts) == 2:
        try:
            return (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return (99, 99)
    return (99, 99)


def _process_time_string(time_str: str, shift: Shift, day_type: Optional[DayType]) -> list:
    if not isinstance(time_str, str): return []
    consultations = []
    # Пробуем найти явный диапазон "ЧЧ:ММ-ЧЧ:ММ"
    match_range = re.search(r'(\d{1,2}[.:]\d{2})\s*-\s*(\d{1,2}[.:]\d{2})', time_str)
    if match_range:
        start_str, end_str = match_range.groups()
        start_obj = parse_time_str(start_str)
        end_obj = parse_time_str(end_str)
        if start_obj and end_obj:
            return [{'original_time': time_str, 'start_time': start_str.replace('.', ':'),
                     'end_time': end_str.replace('.', ':')}]

    # Если диапазона нет, ищем просто время начала и вычисляем конец по звонкам
    match_start = re.search(r'(\d{1,2}[.:]\d{2})', time_str)
    if match_start:
        start_str = match_start.group(1).replace('.', ':')
        # Определяем урок по времени, чтобы найти конец
        try:
            h = int(start_str.split(':')[0])
            calc_shift = Shift.SECOND if h >= 13 else shift
            end_str = get_end_time(start_str, calc_shift, day_type)
            if end_str:
                return [{'original_time': time_str, 'start_time': start_str, 'end_time': end_str}]
        except:
            pass
    return []


def _map_column_indices(df_columns) -> Tuple[Optional[int], Dict[str, Tuple[int, int]]]:
    """Находит индекс колонки учителя и сопоставляет индексы для каждого дня недели."""
    days_map = {
        "понедельник": "Понедельник", "вторник": "Вторник", "среда": "Среда",
        "четверг": "Четверг", "пятница": "Пятница", "суббота": "Суббота"
    }

    teacher_col_idx = None
    day_col_indices = {}

    # Ищем колонку учителя
    for i, col_tuple in enumerate(df_columns):
        full_col_name = " ".join(map(str, col_tuple)).lower()
        if 'учитель' in full_col_name or 'фио' in full_col_name:
            teacher_col_idx = i
            break

    # Ищем колонки для дней недели
    for day_key, day_name in days_map.items():
        time_idx, room_idx = -1, -1
        for i, col_tuple in enumerate(df_columns):
            col_str = " ".join(map(str, col_tuple)).lower()
            if day_key in col_str:
                if 'время' in col_str:
                    time_idx = i
                elif 'каб' in col_str:
                    room_idx = i
        if time_idx != -1:
            day_col_indices[day_name] = (time_idx, room_idx)

    return teacher_col_idx, day_col_indices


# --- ГЛАВНАЯ ФУНКЦИЯ, ТЕПЕРЬ ОНА ЧИЩЕ ---

def parse_consultations(xls: pd.ExcelFile, day_type_override: Optional[DayType] = None) -> Dict[
    str, List[Consultation]]:
    """
    Парсит все листы с консультациями в Excel-файле и возвращает единый словарь.
    """
    days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    consultations_by_day = {day: [] for day in days_order}

    log.info("Запуск парсера консультаций...")
    for sheet_name in xls.sheet_names:
        # 1. Проверяем, подходит ли лист для парсинга
        if 'консультац' not in sheet_name.lower():
            log.info(f"  [✗] Пропуск листа '{sheet_name}': не является листом консультаций.")
            continue

        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=[0, 1])

            teacher_col_idx, day_col_indices = _map_column_indices(df.columns)

            if teacher_col_idx is None:
                log.warning(f"  [✗] Пропуск листа '{sheet_name}': не найдена колонка 'Учитель'/'ФИО'.")
                continue

            log.info(f"  [✓] Анализ листа '{sheet_name}'...")

            # 2. Итерируемся по строкам и извлекаем данные
            for row_idx in range(len(df)):
                teacher = str(df.iloc[row_idx, teacher_col_idx]).strip()
                if not teacher or teacher == 'nan': continue

                for day_name, (time_idx, room_idx) in day_col_indices.items():
                    time_val = str(df.iloc[row_idx, time_idx]).strip()
                    if not time_val or time_val == 'nan': continue

                    room_val = str(df.iloc[row_idx, room_idx]).strip().replace('.0', '') if room_idx != -1 else '—'
                    if not room_val or room_val == 'nan': room_val = '—'

                    shift = Shift.SECOND if "2смена" in sheet_name.lower().replace(" ", "") else Shift.FIRST
                    day_type = day_type_override or DayType.NORMAL

                    processed_times = _process_time_string(time_val, shift, day_type)
                    for time_data in processed_times:
                        consultations_by_day[day_name].append(Consultation(
                            teacher=teacher,
                            time=time_data['original_time'],
                            room=room_val,
                            start_time=time_data['start_time'],
                            end_time=time_data['end_time']
                        ))
        except Exception as e:
            log.error(f"  [!] Произошла ошибка при парсинге листа '{sheet_name}': {e}", exc_info=True)

    # 3. Сортировка результатов
    for day in consultations_by_day:
        consultations_by_day[day].sort(key=lambda x: _parse_consultation_time_for_sort(x.time))

    log.info("Парсер консультаций завершил работу.")
    return consultations_by_day