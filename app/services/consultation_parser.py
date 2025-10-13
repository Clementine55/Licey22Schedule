import pandas as pd
import logging
import re
from .data_validator import parse_time_str
from .bell_schedule import get_end_time

log = logging.getLogger(__name__)


def _parse_consultation_time_for_sort(time_str: str) -> tuple:
    if not isinstance(time_str, str):
        return (99, 99)
    # Используем первую временную метку для сортировки
    first_time = time_str.split(',')[0].strip()
    time_for_sort = first_time.split('-')[0].strip().replace('.', ':')

    parts = time_for_sort.split(':')
    if len(parts) == 2:
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            return (hour, minute)
        except (ValueError, IndexError):
            return (99, 99)
    return (99, 99)


def _process_time_string(time_str: str, shift: str, day_type: str) -> list:
    """
    Обрабатывает сложные строки времени, такие как '10.05-10.45, 15.55-16.40' или '14.15'.
    Возвращает список словарей, каждый из которых представляет одну консультацию.
    """
    if not isinstance(time_str, str):
        return []

    # Нормализуем строку: заменяем точки и унифицируем разделители
    normalized_str = time_str.replace('.', ':').strip()
    # Разделяем строку по запятым, чтобы обработать несколько временных слотов
    time_slots = [slot.strip() for slot in normalized_str.split(',')]

    consultations = []

    # Сначала проверим, является ли это объединенным интервалом (например, 13:25-14:05, 14:15-14:55)
    if len(time_slots) == 2:
        try:
            start1_str, end1_str = [t.strip() for t in time_slots[0].split('-')]
            start2_str, end2_str = [t.strip() for t in time_slots[1].split('-')]

            end1_obj = parse_time_str(end1_str)
            start2_obj = parse_time_str(start2_str)

            # Если конец первого интервала и начало второго очень близки (например, перерыв 10 минут)
            if start2_obj and end1_obj and (start2_obj.hour * 60 + start2_obj.minute) - (
                    end1_obj.hour * 60 + end1_obj.minute) <= 15:
                consultations.append({
                    'original_time': time_str,
                    'start_time': start1_str,
                    'end_time': end2_str
                })
                return consultations  # Возвращаем одну объединенную консультацию
        except (ValueError, IndexError):
            # Если не получается распарсить как два интервала, продолжаем обычную логику
            pass

    # Если это не объединенный интервал, обрабатываем каждый слот отдельно
    for slot in time_slots:
        parts = [p.strip() for p in slot.split('-')]
        start_time = None
        end_time = None

        if len(parts) >= 1 and parts[0]:
            start_time = parts[0]
            # Проверяем формат ЧЧ:ММ
            if not re.match(r'^\d{1,2}:\d{2}$', start_time):
                continue  # Пропускаем некорректный формат

        if len(parts) == 2 and parts[1]:
            end_time = parts[1]
            if not re.match(r'^\d{1,2}:\d{2}$', end_time):
                end_time = None  # Игнорируем некорректное время окончания

        # Если время окончания не указано, пытаемся получить его из bell_schedule
        if start_time and not end_time:
            # Преобразуем "08:30" в "8:30" для поиска
            try:
                h, m = start_time.split(':')
                lookup_time = f"{int(h)}:{m}"
                end_time = get_end_time(lookup_time, shift, day_type)
            except (ValueError, IndexError):
                pass  # Оставляем end_time как None, если формат времени начала некорректен

        if start_time and end_time:
            consultations.append({
                'original_time': slot,  # Для разделенных консультаций показываем только их часть времени
                'start_time': start_time,
                'end_time': end_time
            })

    return consultations


def parse_consultations(file_path: str):
    """
    Parses all 'Консультации' sheets, handling complex time strings.
    """
    days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    consultations_by_day = {day: [] for day in days_order}

    try:
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')
        consultation_sheet_names = [s for s in xls_dict.keys() if 'консультац' in str(s).lower()]

        if not consultation_sheet_names:
            log.info("No consultation sheets found.")
            return consultations_by_day

        for sheet_name in consultation_sheet_names:
            log.info(f"Processing consultation sheet: '{sheet_name}'...")
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=[0, 1], engine='calamine')
            df.columns = ['_'.join(filter(lambda x: 'Unnamed' not in str(x), map(str, col))).strip() for col in
                          df.columns.values]

            teacher_col = next((c for c in df.columns if 'учитель' in c.lower() or 'фио' in c.lower()), None)
            if not teacher_col:
                log.warning(f"Skipping sheet '{sheet_name}': no teacher column found.")
                continue

            df = df.rename(columns={teacher_col: 'Учитель'}).dropna(subset=['Учитель']).fillna('')

            for _, row in df.iterrows():
                teacher = str(row['Учитель']).strip()
                if not teacher: continue

                for day in days_order:
                    day_lower = day.lower()
                    time_col = next((c for c in df.columns if day_lower in c.lower() and 'время' in c.lower()), None)
                    room_col = next((c for c in df.columns if day_lower in c.lower() and 'каб' in c.lower()), None)

                    if time_col and str(row[time_col]).strip():
                        time_val_str = str(row[time_col]).strip()
                        room_val = str(row.get(room_col, '—')).strip() or '—'

                        try:
                            first_hour_str = time_val_str.split(',')[0].split('-')[0].split('.')[0].split(':')[
                                0].strip()
                            first_hour = int(first_hour_str)
                            shift = "2 смена" if first_hour >= 13 else "1 смена"
                        except (ValueError, IndexError):
                            shift = "1 смена"  # Смена по умолчанию, если не удалось определить

                        day_type = "Обычный день"

                        processed_times = _process_time_string(time_val_str, shift, day_type)

                        for time_data in processed_times:
                            consultations_by_day[day].append({
                                'teacher': teacher,
                                'time': time_data['original_time'],
                                'start_time': time_data['start_time'],
                                'end_time': time_data['end_time'],
                                'room': room_val
                            })

        for day in consultations_by_day:
            consultations_by_day[day].sort(key=lambda x: _parse_consultation_time_for_sort(x['time']))

        return consultations_by_day

    except Exception as e:
        log.error(f"Error parsing consultations from '{file_path}': {e}", exc_info=True)
        return {day: [] for day in days_order}