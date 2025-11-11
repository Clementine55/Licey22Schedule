import pandas as pd
import logging
import re
from dataclasses import dataclass
from typing import Optional

# Импорты утилит
from app.services.utils.data_validator import parse_time_str
from app.services.utils.bell_schedule import get_end_time

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


def _process_time_string(time_str: str, shift: str, day_type: str) -> list:
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
            calc_shift = "2 смена" if h >= 13 else shift  # Корректируем смену по времени
            end_str = get_end_time(start_str, calc_shift, day_type)
            if end_str:
                return [{'original_time': time_str, 'start_time': start_str, 'end_time': end_str}]
        except:
            pass
    return []


# ------------------------------------------------------------------

def parse_consultations(xls: pd.ExcelFile, day_type_override: str = None):
    days_map = {
        "понедельник": "Понедельник", "вторник": "Вторник", "среда": "Среда",
        "четверг": "Четверг", "пятница": "Пятница", "суббота": "Суббота"
    }
    consultations_by_day = {day: [] for day in days_map.values()}

    try:
        cons_sheets = [s for s in xls.sheet_names if 'консультац' in s.lower()]

        if not cons_sheets:
            return consultations_by_day

        for sheet_name in cons_sheets:
            log.info(f"Парсинг консультаций с листа: '{sheet_name}'")
            # 2. Читаем лист с header=[0, 1] (двухуровневый заголовок)
            df = pd.read_excel(xls, sheet_name=sheet_name, header=[0, 1])

            # 3. Ищем колонку учителя. col - это кортеж ('Учитель', 'Unnamed...')
            teacher_col_idx = -1
            for i, col_tuple in enumerate(df.columns):
                # Собираем все части заголовка в одну строку для поиска
                full_col_name = " ".join(map(str, col_tuple)).lower()
                if 'учитель' in full_col_name or 'фио' in full_col_name:
                    teacher_col_idx = i
                    break

            if teacher_col_idx == -1:
                log.warning(f"Колонка 'Учитель' не найдена на листе '{sheet_name}'.")
                continue

            # 4. Составляем карту индексов колонок: { "понедельник": (idx_time, idx_room), ... }
            day_col_indices = {}
            for day_key in days_map.keys():
                time_idx, room_idx = -1, -1
                for i, col_tuple in enumerate(df.columns):
                    col_str = " ".join(map(str, col_tuple)).lower()
                    if day_key in col_str:
                        if 'время' in col_str:
                            time_idx = i
                        elif 'каб' in col_str:
                            room_idx = i
                if time_idx != -1:
                    day_col_indices[days_map[day_key]] = (time_idx, room_idx)

            # 5. Итерируемся по строкам и достаем данные по индексам
            for row_idx in range(len(df)):
                teacher = str(df.iloc[row_idx, teacher_col_idx]).strip()
                if not teacher or teacher == 'nan': continue

                for day_name, (time_idx, room_idx) in day_col_indices.items():
                    time_val = str(df.iloc[row_idx, time_idx]).strip()
                    if not time_val or time_val == 'nan': continue

                    room_val = '—'
                    if room_idx != -1:
                        r_val = str(df.iloc[row_idx, room_idx]).strip()
                        if r_val and r_val != 'nan':
                            room_val = r_val.replace('.0', '')  # Убираем .0 от чисел

                    # Определяем смену и парсим время
                    shift = "1 смена"  # Дефолт
                    if "1смена" in sheet_name.lower().replace(" ", ""):
                        shift = "1 смена"
                    elif "2смена" in sheet_name.lower().replace(" ", ""):
                        shift = "2 смена"

                    day_type = day_type_override or "Обычный день"

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
        log.error(f"Ошибка парсинга консультаций: {e}", exc_info=True)

    # Сортировка
    for day in consultations_by_day:
        consultations_by_day[day].sort(key=lambda x: _parse_consultation_time_for_sort(x.time))

    return consultations_by_day