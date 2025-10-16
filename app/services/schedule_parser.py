# app/services/schedule_parser.py (Финальная, 100% рабочая версия)

import pandas as pd
import logging
import re
from itertools import groupby
from datetime import datetime, time, timedelta
from .data_validator import is_valid_class_name, normalize_class_name, parse_time_str
from .bell_schedule import get_end_time, get_default_lesson_duration

log = logging.getLogger(__name__)


def _normalize_start_time_string(time_str: str) -> str:
    if not isinstance(time_str, str): return ""
    start_time = time_str.split('-')[0].strip().split('–')[0].strip()
    normalized = start_time.replace('.', ':')
    parts = normalized.split(':')
    if len(parts) == 2:
        try:
            hour = int(parts[0]); minute = parts[1]
            return f"{hour}:{minute}"
        except (ValueError, IndexError): return normalized
    return normalized

def get_shift_from_time(time_str: str) -> str:
    try:
        hour_str = time_str.split('.')[0].split(':')[0]
        hour = int(re.match(r'(\d+)', hour_str).group(1))
        return "2 смена" if hour >= 12 else "1 смена"
    except (ValueError, IndexError, AttributeError): return "1 смена"

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


def _process_grade_group(grade_classes: dict, grade_num: int, shift_name: str, day_type: str):
    grade_class_names = sorted(grade_classes.keys())

    # --- Шаг 1: Найти ПРАВИЛЬНОЕ время окончания, проверив ВСЕ уроки во ВСЕХ классах ---
    last_lesson_end_time_obj = None
    all_valid_start_times = []
    for lessons in grade_classes.values():
        for lesson in lessons:
            if lesson.get('предмет') and lesson['предмет'] != '—':
                if lesson.get('start_time'):
                    all_valid_start_times.append(lesson['start_time'])
                if lesson.get('end_time'):
                    end_time_obj = parse_time_str(lesson['end_time'])
                    if end_time_obj and (last_lesson_end_time_obj is None or end_time_obj > last_lesson_end_time_obj):
                        last_lesson_end_time_obj = end_time_obj

    if not all_valid_start_times:
        return None

    # --- Шаг 2: Сгенерировать строки для отображения в таблице ---
    time_grid = sorted(
        list(set(lesson['время'] for lessons in grade_classes.values() for lesson in lessons if lesson['предмет'] != '—')),
        key=lambda x: parse_time_str(_normalize_start_time_string(x))
    )
    schedule_rows = []
    for lesson_time in time_grid:
        row = {'время': lesson_time, 'предметы': {}}
        first_lesson_in_row = None
        for class_name in grade_class_names:
            lesson = next((l for l in grade_classes.get(class_name, []) if l['время'] == lesson_time and l['предмет'] != '—'), None)
            row['предметы'][class_name] = lesson['предмет'] if lesson else ''
            if not first_lesson_in_row and lesson:
                first_lesson_in_row = lesson
        if first_lesson_in_row:
            start_time_obj = first_lesson_in_row.get('start_time')
            row['урок'] = first_lesson_in_row.get('урок')
            row['start_time'] = start_time_obj.strftime('%H:%M') if start_time_obj else ''
            row['end_time'] = first_lesson_in_row.get('end_time')
        schedule_rows.append(row)

    # --- Шаг 3: "Запасной план", если время окончания так и не нашлось ---
    if not last_lesson_end_time_obj:
        default_duration = get_default_lesson_duration(shift_name, day_type)
        last_start_time = max(all_valid_start_times)
        last_lesson_end_time_obj = (datetime.combine(datetime.today(), last_start_time) + timedelta(minutes=default_duration)).time()

    return {
        'grade_key': f"{grade_num}-е классы ({shift_name})",
        'class_names': grade_class_names,
        'schedule_rows': schedule_rows,
        'first_lesson_time': min(all_valid_start_times),
        'last_lesson_end_time': last_lesson_end_time_obj
    }


def parse_schedule(file_path: str, day_type_override: str = None):
    try:
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')
        raw_data = {}
        for sheet_name, df in xls_dict.items():
            required_columns = ['Дни', 'Уроки', 'Время']
            if not all(col in df.columns for col in required_columns): continue
            class_name_map = {col: normalize_class_name(str(col)) for col in df.columns if is_valid_class_name(str(col))}
            if not class_name_map: continue
            df['Дни'] = df['Дни'].ffill()
            df = df.fillna('')
            sheet_day_type = day_type_override or _get_day_type_from_sheet_name(sheet_name)
            sheet_shift = _get_shift_from_sheet_name(sheet_name)
            log.info(f"Processing sheet: '{sheet_name}'. Shift: '{sheet_shift}', Day Type: '{sheet_day_type}'")
            for day_name, day_group in df.groupby('Дни'):
                if day_name not in raw_data: raw_data[day_name] = {"1 смена": {}, "2 смена": {}}
                master_day_grid = []
                for _, row in day_group.iterrows():
                    if row['Уроки'] != '' and row['Время'] != '':
                        master_day_grid.append({'урок': row['Уроки'], 'время': row['Время'], 'start_time': parse_time_str(row['Время']), 'original_row': row})
                if not master_day_grid: continue
                for original_name, normalized_name in class_name_map.items():
                    if not any(str(lesson_info['original_row'][original_name]).strip() for lesson_info in master_day_grid): continue
                    actual_shift = sheet_shift or get_shift_from_time(next((info['время'] for info in master_day_grid if str(info['original_row'][original_name]).strip()),"8:00"))
                    lessons = []
                    for lesson_info in master_day_grid:
                        subject = str(lesson_info['original_row'][original_name]).strip()
                        original_start_time = lesson_info['время']
                        start_time_for_lookup = _normalize_start_time_string(original_start_time)
                        end_time_str = get_end_time(start_time_for_lookup, actual_shift, sheet_day_type)
                        if end_time_str:
                            display_time = f"{start_time_for_lookup}–{end_time_str}"
                        else:
                            display_time = original_start_time
                        lessons.append({
                            'урок': lesson_info['урок'],
                            'время': display_time,
                            'предмет': subject or '—',
                            'start_time': parse_time_str(start_time_for_lookup),
                            'end_time': end_time_str
                        })
                    raw_data[day_name][actual_shift][normalized_name] = lessons
        final_schedule = {}
        days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        for day in days_order:
            if day not in raw_data: final_schedule[day] = None; continue
            day_data = {"portrait_view": {}, "landscape_view": {}}
            all_classes_for_day = {**raw_data[day]["1 смена"], **raw_data[day]["2 смена"]}
            for class_name, lessons_list in all_classes_for_day.items():
                valid_lessons = [l for l in lessons_list if l['start_time'] and l['предмет'] != '—']
                if not valid_lessons: continue
                last_lesson_end = max([parse_time_str(l['end_time']) for l in valid_lessons if l.get('end_time')] or [time(0, 0)])
                day_data["portrait_view"][class_name] = {
                    'lessons': lessons_list,
                    'first_lesson_time': min(l['start_time'] for l in valid_lessons),
                    'last_lesson_end_time': last_lesson_end
                }
            temp_landscape_view = {}
            for shift_name in ["1 смена", "2 смена"]:
                classes_in_shift = raw_data[day][shift_name]
                if not classes_in_shift: continue
                get_grade = lambda item: int(re.match(r'(\d+)', item[0]).group(1))
                for grade_num, grade_iter in groupby(sorted(classes_in_shift.items(), key=get_grade), key=get_grade):
                    if grade_num < 5: continue
                    schedule_data = _process_grade_group(dict(grade_iter), grade_num, shift_name, sheet_day_type)
                    if schedule_data: temp_landscape_view[schedule_data['grade_key']] = schedule_data
            day_data["landscape_slides"] = []
            sorted_keys = sorted(temp_landscape_view.keys(), key=lambda k: (int(re.search(r'(\d+)', k).group(1)), k))
            i = 0
            while i < len(sorted_keys):
                group1_data = temp_landscape_view[sorted_keys[i]]
                if i + 1 < len(sorted_keys):
                    group2_data = temp_landscape_view[sorted_keys[i + 1]]
                    if len(group1_data['schedule_rows']) + len(group2_data['schedule_rows']) > 16:
                        day_data["landscape_slides"].append([group1_data]); i += 1
                    else:
                        day_data["landscape_slides"].append([group1_data, group2_data]); i += 2
                else:
                    day_data["landscape_slides"].append([group1_data]); i += 1
            final_schedule[day] = day_data
        return final_schedule
    except Exception as e:
        log.critical(f"Critical error parsing schedule file '{file_path}': {e}", exc_info=True)
        return None