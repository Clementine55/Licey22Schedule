# app/services/consultation_parser.py (Финальная версия)

import pandas as pd
import logging
import re
from .data_validator import parse_time_str
from .bell_schedule import get_end_time

log = logging.getLogger(__name__)


def _parse_consultation_time_for_sort(time_str: str) -> tuple:
    # ... (код без изменений)
    if not isinstance(time_str, str): return (99, 99)
    first_time = time_str.split(',')[0].strip()
    time_for_sort = first_time.split('-')[0].strip().replace('.', ':')
    parts = time_for_sort.split(':')
    if len(parts) == 2:
        try:
            hour = int(parts[0]);
            minute = int(parts[1])
            return (hour, minute)
        except (ValueError, IndexError):
            return (99, 99)
    return (99, 99)


def _process_time_string(time_str: str, shift: str, day_type: str) -> list:
    # ... (код без изменений)
    if not isinstance(time_str, str): return []
    normalized_str = time_str.replace('.', ':').strip()
    time_slots = [slot.strip() for slot in normalized_str.split(',')]
    consultations = []
    if len(time_slots) == 2:
        try:
            start1_str, end1_str = [t.strip() for t in time_slots[0].split('-')]
            start2_str, end2_str = [t.strip() for t in time_slots[1].split('-')]
            end1_obj = parse_time_str(end1_str)
            start2_obj = parse_time_str(start2_str)
            if start2_obj and end1_obj and (start2_obj.hour * 60 + start2_obj.minute) - (
                    end1_obj.hour * 60 + end1_obj.minute) <= 15:
                consultations.append({'original_time': time_str, 'start_time': start1_str, 'end_time': end2_str})
                return consultations
        except (ValueError, IndexError):
            pass
    for slot in time_slots:
        parts = [p.strip() for p in slot.split('-')]
        start_time, end_time = None, None
        if len(parts) >= 1 and parts[0]:
            start_time = parts[0]
            if not re.match(r'^\d{1,2}:\d{2}$', start_time): continue
        if len(parts) == 2 and parts[1]:
            end_time = parts[1]
            if not re.match(r'^\d{1,2}:\d{2}$', end_time): end_time = None
        if start_time and not end_time:
            try:
                h, m = start_time.split(':')
                lookup_time = f"{int(h)}:{m}"
                # Вот здесь используется day_type
                end_time = get_end_time(lookup_time, shift, day_type)
            except (ValueError, IndexError):
                pass
        if start_time and end_time:
            consultations.append({'original_time': slot, 'start_time': start_time, 'end_time': end_time})
    return consultations


# --- ИЗМЕНЕНИЕ: Функция принимает day_type_override ---
def parse_consultations(file_path: str, day_type_override: str = None):
    days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    consultations_by_day = {day: [] for day in days_order}
    try:
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')
        consultation_sheet_names = [s for s in xls_dict.keys() if 'консультац' in str(s).lower()]
        if not consultation_sheet_names: return consultations_by_day
        for sheet_name in consultation_sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=[0, 1], engine='calamine')
            df.columns = ['_'.join(filter(lambda x: 'Unnamed' not in str(x), map(str, col))).strip() for col in
                          df.columns.values]
            teacher_col = next((c for c in df.columns if 'учитель' in c.lower() or 'фио' in c.lower()), None)
            if not teacher_col: continue
            df = df.rename(columns={teacher_col: 'Учитель'}).dropna(subset=['Учитель']).fillna('')
            for _, row in df.iterrows():
                teacher = str(row['Учитель']).strip()
                if not teacher: continue
                for day in days_order:
                    day_lower = day.lower()
                    time_col = next((c for c in df.columns if day_lower in c.lower() and 'время' in c.lower()), None)
                    room_col = next((c for c in df.columns if day_lower in c.lower() and 'каб' in c.lower()), None)
                    if time_col and str(row[time_col]).strip():
                        time_val_str, room_val = str(row[time_col]).strip(), str(row.get(room_col, '—')).strip() or '—'
                        try:
                            first_hour = int(
                                time_val_str.split(',')[0].split('-')[0].split('.')[0].split(':')[0].strip())
                            shift = "2 смена" if first_hour >= 13 else "1 смена"
                        except (ValueError, IndexError):
                            shift = "1 смена"

                        # Передаем day_type_override дальше
                        day_type = day_type_override or "Обычный день"
                        processed_times = _process_time_string(time_val_str, shift, day_type)
                        for time_data in processed_times:
                            consultations_by_day[day].append({'teacher': teacher, 'time': time_data['original_time'],
                                                              'start_time': time_data['start_time'],
                                                              'end_time': time_data['end_time'], 'room': room_val})
        for day in consultations_by_day:
            consultations_by_day[day].sort(key=lambda x: _parse_consultation_time_for_sort(x['time']))
        return consultations_by_day
    except Exception as e:
        log.error(f"Error parsing consultations from '{file_path}': {e}", exc_info=True)
        return {day: [] for day in days_order}