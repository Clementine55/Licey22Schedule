import pandas as pd
import logging
import re
from itertools import groupby
from datetime import datetime
from .data_validator import is_valid_class_name, normalize_class_name, parse_time_str

log = logging.getLogger(__name__)


def get_shift_from_time(time_str: str) -> str:
    try:
        hour_str = time_str.split('.')[0]
        hour = int(re.match(r'(\d+)', hour_str).group(1))
        return "2 смена" if hour >= 12 else "1 смена"
    except (ValueError, IndexError, AttributeError):
        return "1 смена"


def _get_shift_from_sheet_name(sheet_name: str) -> str or None:
    if '(1 смена)' in sheet_name.lower():
        return "1 смена"
    if '(2 смена)' in sheet_name.lower():
        return "2 смена"
    return None


def parse_schedule(file_path: str):
    try:
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')
        raw_data = {}

        for sheet_name, df in xls_dict.items():
            required_columns = ['Дни', 'Уроки', 'Время']
            if not all(col in df.columns for col in required_columns):
                log.warning(f"Лист '{sheet_name}' проигнорирован: нет обязательных колонок.")
                continue

            class_name_map = {
                col: normalize_class_name(str(col))
                for col in df.columns if is_valid_class_name(str(col))
            }
            if not class_name_map:
                log.warning(f"Лист '{sheet_name}' проигнорирован: не найдены классы.")
                continue

            df['Дни'] = df['Дни'].ffill()
            df = df.fillna('')
            sheet_shift = _get_shift_from_sheet_name(sheet_name)

            for day_name, day_group in df.groupby('Дни'):
                if day_name not in raw_data:
                    raw_data[day_name] = {"1 смена": {}, "2 смена": {}}

                master_day_grid = []
                for _, row in day_group.iterrows():
                    if row['Уроки'] != '' and row['Время'] != '':
                        master_day_grid.append({
                            'урок': row['Уроки'], 'время': row['Время'],
                            'start_time': parse_time_str(row['Время']), 'original_row': row
                        })
                if not master_day_grid: continue

                for original_name, normalized_name in class_name_map.items():
                    lessons, has_any_subject = [], False
                    for lesson_info in master_day_grid:
                        subject = str(lesson_info['original_row'][original_name]).strip()
                        if subject: has_any_subject = True
                        lessons.append({
                            'урок': lesson_info['урок'], 'время': lesson_info['время'],
                            'предмет': subject or '—', 'start_time': lesson_info['start_time']
                        })
                    if has_any_subject:
                        first_lesson = next((l for l in lessons if l['предмет'] != '—'), None)
                        actual_shift = sheet_shift or get_shift_from_time(
                            first_lesson['время']) if first_lesson else "1 смена"
                        raw_data[day_name][actual_shift][normalized_name] = lessons

        final_schedule = {}
        days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

        for day in days_order:
            if day not in raw_data:
                final_schedule[day] = None
                continue

            day_data = {"portrait_view": {}, "landscape_view": {}}
            all_classes_for_day = {**raw_data[day]["1 смена"], **raw_data[day]["2 смена"]}

            # --- Формируем Portrait View ---
            for class_name, lessons in all_classes_for_day.items():
                valid_lessons = [l for l in lessons if l['start_time'] and l['предмет'] != '—']
                if not valid_lessons: continue
                day_data["portrait_view"][class_name] = {
                    'lessons': lessons,
                    'first_lesson_time': min(l['start_time'] for l in valid_lessons),
                    'last_lesson_end_time': (datetime.combine(datetime.today(), max(
                        l['start_time'] for l in valid_lessons)) + pd.Timedelta(minutes=40)).time()
                }
            day_data["portrait_view"] = dict(sorted(day_data["portrait_view"].items(),
                                                    key=lambda item: (int(re.search(r'(\d+)', item[0]).group(1)),
                                                                      item[0])))

            # --- Формируем Landscape View ---
            for shift_name in ["1 смена", "2 смена"]:
                classes_in_shift = raw_data[day][shift_name]
                if not classes_in_shift: continue
                get_grade = lambda item: int(re.match(r'(\d+)', item[0]).group(1))
                for grade_num, grade_iter in groupby(sorted(classes_in_shift.items(), key=get_grade), key=get_grade):
                    grade_classes = dict(grade_iter)
                    grade_class_names = sorted(grade_classes.keys())
                    all_lessons_info, time_grid = {}, set()

                    for lessons_inner in grade_classes.values():
                        for lesson in lessons_inner:
                            if lesson['предмет'] != '—':
                                all_lessons_info[lesson['время']] = {'урок': lesson['урок'],
                                                                     'start_time': lesson['start_time']}
                                time_grid.add(lesson['время'])

                    if not time_grid: continue

                    schedule_rows = []
                    for lesson_time in sorted(list(time_grid), key=parse_time_str):
                        row = {'время': lesson_time, 'предметы': {}, 'урок': all_lessons_info[lesson_time]['урок']}
                        for cn in grade_class_names:
                            lesson = next((l for l in grade_classes.get(cn, []) if
                                           l['время'] == lesson_time and l['предмет'] != '—'), None)
                            row['предметы'][cn] = lesson['предмет'] if lesson else ''
                        schedule_rows.append(row)

                    valid_times = [v['start_time'] for v in all_lessons_info.values() if v['start_time']]
                    if not valid_times: continue

                    grade_key = f"{grade_num}-е классы ({shift_name})"
                    day_data["landscape_view"][grade_key] = {
                        'class_names': grade_class_names, 'schedule_rows': schedule_rows,
                        'first_lesson_time': min(valid_times),
                        'last_lesson_end_time': (datetime.combine(datetime.today(), max(valid_times)) + pd.Timedelta(
                            minutes=40)).time()
                    }

            final_schedule[day] = day_data
        return final_schedule
    except Exception as e:
        log.critical(f"Критическая ошибка при парсинге файла '{file_path}': {e}", exc_info=True)
        return None

