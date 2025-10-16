# app/routes.py (Финальная, исправленная версия)

import time
import os
import logging
from flask import Blueprint, render_template, abort, redirect, url_for
from datetime import datetime, timedelta, time as time_obj
from config import Config

# Импортируем все наши сервисы, включая новые
from .services import (
    yandex_disk_client,
    schedule_parser,
    time_service,
    consultation_parser,
    short_day_parser  # Сервис для определения типа дня
)
from .utils import make_json_serializable

log = logging.getLogger(__name__)
bp = Blueprint('main', __name__)


@bp.route('/')
def root():
    # Перенаправляем на первое расписание из конфига по умолчанию
    try:
        default_schedule_name = next(iter(Config.SCHEDULES))
        return redirect(url_for('main.index', schedule_name=default_schedule_name))
    except StopIteration:
        # Обработка случая, если SCHEDULES пуст
        abort(500, description="No schedules configured.")


@bp.route('/<schedule_name>')
def index(schedule_name):
    if schedule_name not in Config.SCHEDULES:
        abort(404)

    # --- 1. ПРОВЕРКА И ЗАГРУЗКА ФАЙЛА (КЭШИРОВАНИЕ) ---
    schedule_config = Config.SCHEDULES[schedule_name]
    yandex_file_path, local_file_path = schedule_config['yandex_path'], schedule_config['local_path']
    cache_duration = Config.CACHE_DURATION

    if not os.path.exists(local_file_path) or (time.time() - os.path.getmtime(local_file_path)) > cache_duration:
        log.info(f"Кэш для '{schedule_name}' устарел или отсутствует. Запускаю скачивание...")
        yandex_disk_client.download_schedule_file(yandex_file_path, local_file_path)

    if not os.path.exists(local_file_path):
        return render_template('error.html', message=f"Не удалось загрузить файл расписания '{schedule_name}'.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    # --- 2. ОПРЕДЕЛЕНИЕ ТИПА ТЕКУЩЕГО ДНЯ (НОВАЯ ЛОГИКА) ---
    time_info = time_service.get_current_day_and_time()

    # Всего один вызов, который делает всё!
    is_short_day = short_day_parser.is_today_a_short_day(local_file_path, time_info.date_str_iso)

    # На основе ответа (True/False) устанавливаем тип дня
    current_day_type = "Короткий день" if is_short_day else "Обычный день"

    if is_short_day:
        log.warning(f"Сегодня ({time_info.date_str_iso}) определен как КОРОТКИЙ ДЕНЬ.")

    # --- 3. ПАРСИНГ ДАННЫХ С УЧЕТОМ ТИПА ДНЯ ---
    full_schedule = schedule_parser.parse_schedule(local_file_path, day_type_override=current_day_type)
    all_consultations = consultation_parser.parse_consultations(local_file_path)

    if not full_schedule:
        return render_template('error.html', message="Файл расписания поврежден или имеет неверный формат.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    # --- 4. ФИЛЬТРАЦИЯ ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ (ЛОГИКА ОСТАЕТСЯ ПРЕЖНЕЙ) ---
    active_day_name = time_info.day_name
    current_time = time_info.time_obj
    current_date = time_info.date_str_display

    schedule_for_today = full_schedule.get(active_day_name)
    today_date_obj = datetime.strptime(time_info.date_str_iso, '%Y-%m-%d').date()
    current_dt = datetime.combine(today_date_obj, current_time)

    # Фильтрация уроков
    if schedule_for_today:
        initial_slides = schedule_for_today.get("landscape_slides", [])
        active_grade_groups = []
        if initial_slides:
            for slide in initial_slides:
                for grade_data in slide:
                    start_dt = datetime.combine(today_date_obj, grade_data['first_lesson_time']) - timedelta(
                        minutes=Config.SHOW_BEFORE_START_MIN)
                    end_dt = datetime.combine(today_date_obj, grade_data['last_lesson_end_time']) + timedelta(
                        minutes=Config.SHOW_AFTER_END_MIN)
                    if start_dt <= current_dt <= end_dt:
                        active_grade_groups.append(grade_data)

        # Перегруппировка слайдов после фильтрации
        filtered_slides = []
        i = 0
        while i < len(active_grade_groups):
            g1 = active_grade_groups[i]
            if i + 1 < len(active_grade_groups) and len(g1['schedule_rows']) + len(
                    active_grade_groups[i + 1]['schedule_rows']) <= 16:
                filtered_slides.append([g1, active_grade_groups[i + 1]])
                i += 2
            else:
                filtered_slides.append([g1])
                i += 1
        schedule_for_today["landscape_slides"] = filtered_slides
    else:
        schedule_for_today = {"landscape_slides": []}

    # Фильтрация консультаций
    raw_consultations_for_today = all_consultations.get(active_day_name, [])
    consultations_for_today = []
    if raw_consultations_for_today:
        try:
            first_start_time = min(
                datetime.strptime(c['start_time'], '%H:%M').time() for c in raw_consultations_for_today if
                c.get('start_time'))
            last_end_time = max(datetime.strptime(c['end_time'], '%H:%M').time() for c in raw_consultations_for_today if
                                c.get('end_time'))

            start_display_dt = datetime.combine(today_date_obj, first_start_time) - timedelta(
                minutes=Config.SHOW_BEFORE_START_MIN)
            end_display_dt = datetime.combine(today_date_obj, last_end_time) + timedelta(
                minutes=Config.SHOW_AFTER_END_MIN)

            if start_display_dt <= current_dt <= end_display_dt:
                consultations_for_today = raw_consultations_for_today
        except (ValueError, TypeError):
            log.warning("Не удалось отфильтровать консультации по времени из-за некорректных данных.")
            consultations_for_today = raw_consultations_for_today  # Показываем все, если не смогли отфильтровать

    # Финальная проверка, показывать ли сообщение "Занятия завершены"
    lessons_are_over = not schedule_for_today.get("landscape_slides") and not consultations_for_today

    # --- 5. ОТПРАВКА ДАННЫХ В ШАБЛОН ---
    return render_template(
        'index.html',
        schedule_for_today=make_json_serializable(schedule_for_today),
        consultations_for_today=consultations_for_today,
        active_day_name=active_day_name,
        current_date=current_date,
        current_time=current_time.strftime('%H:%M:%S'),
        refresh_interval=cache_duration,
        carousel_interval=Config.CAROUSEL_INTERVAL,
        logo_path=Config.LOGO_FILE_PATH,
        lessons_are_over=lessons_are_over,
        is_weekend=(active_day_name == "Воскресенье"),
        current_schedule_name=schedule_name
    )