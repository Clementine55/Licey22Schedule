import pandas as pd
import logging
import re
from itertools import groupby
from datetime import datetime
from .data_validator import normalize_and_get_class_name, parse_time_str

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
        xls = pd.ExcelFile(file_path)
        raw_data = {}

        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            required_columns = ['Дни', 'Уроки', 'Время']
            if not all(col in df.columns for col in required_columns):
                log.warning(f"Лист '{sheet_name}' проигнорирован: нет обязательных колонок.")
                continue

            class_columns = [col for col in df.columns if normalize_and_get_class_name(str(col))]
            if not class_columns:
                log.warning(f"Лист '{sheet_name}' проигнорирован: не найдены классы.")
                continue

            df['Дни'] = df['Дни'].ffill()
            df = df.fillna('')
            sheet_shift = _get_shift_from_sheet_name(sheet_name)

            for day_name, day_group in df.groupby('Дни'):
                if day_name not in raw_data:
                    raw_data[day_name] = {"1 смена": {}, "2 смена": {}}

                for class_name in class_columns:
                    lessons = []
                    for _, lesson_row in day_group.iterrows():
                        subject = str(lesson_row[class_name]).strip()
                        if subject:
                            lessons.append({
                                'урок': lesson_row['Уроки'],
                                'время': lesson_row['Время'],
                                'предмет': subject,
                                'start_time': parse_time_str(lesson_row['Время'])
                            })

                    if lessons:
                        actual_shift = sheet_shift or get_shift_from_time(lessons[0]['время'])
                        if class_name not in raw_data[day_name][actual_shift]:
                            raw_data[day_name][actual_shift][class_name] = []
                        raw_data[day_name][actual_shift][class_name].extend(lessons)

        final_schedule = {}
        days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

        for day in days_order:
            if day not in raw_data:
                final_schedule[day] = None
                continue

            day_data = {"portrait_view": {}, "landscape_view": {}}

            # --- Формируем Portrait View с данными для фильтрации ---
            all_classes_for_day = {**raw_data[day]["1 смена"], **raw_data[day]["2 смена"]}
            for class_name, lessons in all_classes_for_day.items():
                valid_lessons = [l for l in lessons if l['start_time']]
                if not valid_lessons: continue

                first_lesson_time = min(l['start_time'] for l in valid_lessons)
                last_lesson_start_time = max(l['start_time'] for l in valid_lessons)

                dt_max = datetime.combine(datetime.today(), last_lesson_start_time)
                last_lesson_end_time = (dt_max + pd.Timedelta(minutes=40)).time()

                day_data["portrait_view"][class_name] = {
                    'lessons': lessons,
                    'first_lesson_time': first_lesson_time,
                    'last_lesson_end_time': last_lesson_end_time
                }

            # --- Формируем Landscape View ---
            landscape_view_ordered = {}
            for shift_name in ["1 смена", "2 смена"]:
                classes_in_shift = raw_data[day][shift_name]
                if not classes_in_shift: continue

                get_grade_num = lambda item: int(re.match(r'(\d+)', item[0]).group(1))
                sorted_classes = sorted(classes_in_shift.items(), key=get_grade_num)

                for grade_num, grade_classes_iter in groupby(sorted_classes, key=get_grade_num):
                    # ... (логика для landscape view остается такой же) ...
                    grade_classes = dict(grade_classes_iter)
                    grade_class_names = sorted(grade_classes.keys())

                    all_lesson_times = set()
                    min_start_time, max_end_time = None, None

                    for class_name_inner, lessons_inner in grade_classes.items():
                        for lesson in lessons_inner:
                            all_lesson_times.add(lesson['время'])
                            lesson_start = lesson['start_time']
                            if lesson_start:
                                if not min_start_time or lesson_start < min_start_time:
                                    min_start_time = lesson_start
                                if not max_end_time or lesson_start > max_end_time:
                                    max_end_time = lesson_start

                    if max_end_time:
                        dt_max = datetime.combine(datetime.today(), max_end_time)
                        max_end_time = (dt_max + pd.Timedelta(minutes=40)).time()

                    time_grid = sorted(list(all_lesson_times))

                    schedule_rows = []
                    for lesson_time in time_grid:
                        row = {'время': lesson_time, 'предметы': {}}
                        lesson_num = ''
                        for class_name_inner in grade_class_names:
                            found_lesson = next(
                                (l for l in grade_classes[class_name_inner] if l['время'] == lesson_time), None)
                            if found_lesson:
                                row['предметы'][class_name_inner] = found_lesson['предмет']
                                lesson_num = found_lesson['урок']
                        row['урок'] = lesson_num
                        schedule_rows.append(row)

                    grade_key = f"{grade_num}-е классы ({shift_name})"
                    landscape_view_ordered[grade_key] = {
                        'class_names': grade_class_names,
                        'schedule_rows': schedule_rows,
                        'first_lesson_time': min_start_time,
                        'last_lesson_end_time': max_end_time
                    }

            day_data['landscape_view'] = landscape_view_ordered
            final_schedule[day] = day_data

        return final_schedule

    except Exception as e:
        log.critical(f"Критическая ошибка при парсинге файла '{file_path}': {e}", exc_info=True)
        return None

