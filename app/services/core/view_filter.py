# app/services/view_filter.py

import logging
from datetime import datetime, timedelta, time as time_obj
from config import Config

log = logging.getLogger(__name__)


def filter_schedule_for_display(schedule_for_day: dict, time_info: object) -> dict:
    """
    Фильтрует уроки для ландшафтного режима, показывая только актуальные.
    Возвращает измененный словарь с расписанием на день.
    """
    if not schedule_for_day or not schedule_for_day.get("landscape_slides"):
        return {"landscape_slides": []}

    today_date_obj = datetime.strptime(time_info.date_str_iso, '%Y-%m-%d').date()
    current_dt = datetime.combine(today_date_obj, time_info.time_obj)

    initial_slides = schedule_for_day.get("landscape_slides", [])
    active_grade_groups = []

    for slide in initial_slides:
        for grade_data in slide:
            try:
                # Конвертируем время из строк обратно в объекты time
                first_lesson_time = time_obj.fromisoformat(grade_data['first_lesson_time'])
                last_lesson_end_time = time_obj.fromisoformat(grade_data['last_lesson_end_time'])

                start_dt = datetime.combine(today_date_obj, first_lesson_time) - timedelta(
                    minutes=Config.SHOW_BEFORE_START_MIN)
                end_dt = datetime.combine(today_date_obj, last_lesson_end_time) + timedelta(
                    minutes=Config.SHOW_AFTER_END_MIN)

                if start_dt <= current_dt <= end_dt:
                    active_grade_groups.append(grade_data)
            except (ValueError, TypeError) as e:
                log.warning(f"Ошибка при фильтрации уроков для группы {grade_data.get('grade_key')}: {e}")
                continue

    # Перегруппировка слайдов после фильтрации
    filtered_slides = []
    i = 0
    while i < len(active_grade_groups):
        g1 = active_grade_groups[i]
        g1_rows = len(g1.get('schedule_rows', []))

        if i + 1 < len(active_grade_groups):
            g2 = active_grade_groups[i + 1]
            g2_rows = len(g2.get('schedule_rows', []))

            if g1_rows + g2_rows <= 16:
                filtered_slides.append([g1, g2])
                i += 2
            else:
                filtered_slides.append([g1])
                i += 1
        else:
            filtered_slides.append([g1])
            i += 1

    schedule_for_day["landscape_slides"] = filtered_slides
    return schedule_for_day


def filter_consultations_for_display(consultations_for_day: list, time_info: object) -> list:
    """
    Фильтрует консультации, показывая только актуальные.
    Возвращает отфильтрованный список консультаций.
    """
    if not consultations_for_day:
        return []

    today_date_obj = datetime.strptime(time_info.date_str_iso, '%Y-%m-%d').date()
    current_dt = datetime.combine(today_date_obj, time_info.time_obj)

    try:
        valid_consultations = [c for c in consultations_for_day if c.get('start_time') and c.get('end_time')]
        if not valid_consultations:
            return consultations_for_day  # Возвращаем все, если нет данных для фильтра

        first_start_time = min(time_obj.fromisoformat(c['start_time']) for c in valid_consultations)
        last_end_time = max(time_obj.fromisoformat(c['end_time']) for c in valid_consultations)

        start_display_dt = datetime.combine(today_date_obj, first_start_time) - timedelta(
            minutes=Config.SHOW_BEFORE_START_MIN)
        end_display_dt = datetime.combine(today_date_obj, last_end_time) + timedelta(minutes=Config.SHOW_AFTER_END_MIN)

        if start_display_dt <= current_dt <= end_display_dt:
            return consultations_for_day
        else:
            return []  # Время консультаций еще не пришло или уже прошло

    except (ValueError, TypeError) as e:
        log.warning(f"Не удалось отфильтровать консультации по времени: {e}")
        return consultations_for_day  # В случае ошибки показываем все