# app/routes.py (Финальная, отрефакторенная версия)

import logging
from flask import Blueprint, render_template, abort, redirect, url_for
from config import Config

# Импортируем наш новый сервис фильтрации
from .services.clients import time_service
from .services.core import view_filter, cache_manager

log = logging.getLogger(__name__)
bp = Blueprint('main', __name__)


@bp.route('/')
def root():
    try:
        default_schedule_name = next(iter(Config.SCHEDULES))
        return redirect(url_for('main.index', schedule_name=default_schedule_name))
    except StopIteration:
        abort(500, description="No schedules configured.")


@bp.route('/<schedule_name>')
def index(schedule_name):
    if schedule_name not in Config.SCHEDULES:
        abort(404)

    all_data = cache_manager.get_schedule_data(schedule_name)
    if all_data.get("error"):
        return render_template('error.html', message=f"Ошибка загрузки данных: {all_data['error']}",
                               logo_path=Config.LOGO_FILE_PATH), 500

    time_info = time_service.get_current_day_and_time()

    full_schedule = all_data.get("schedule")
    all_consultations = all_data.get("consultations")

    if not full_schedule or not all_consultations:
        return render_template('error.html', message="Данные в кэше повреждены.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    # --- 4. ФИЛЬТРАЦИЯ ДАННЫХ ЧЕРЕЗ НОВЫЙ СЕРВИС ---
    schedule_for_today = full_schedule.get(time_info.day_name, {})

    # Один вызов вместо 50 строк кода
    filtered_schedule = view_filter.filter_schedule_for_display(schedule_for_today, time_info)

    # И второй вызов для консультаций
    raw_consultations = all_consultations.get(time_info.day_name, [])
    consultations_for_today = view_filter.filter_consultations_for_display(raw_consultations, time_info)

    lessons_are_over = not filtered_schedule.get("landscape_slides") and not consultations_for_today

    # --- 5. ОТПРАВКА ДАННЫХ В ШАБЛОН ---
    return render_template(
        'index.html',
        schedule_for_today=filtered_schedule,
        consultations_for_today=consultations_for_today,
        active_day_name=time_info.day_name,
        current_date=time_info.date_str_display,
        current_time=time_info.time_obj.strftime('%H:%M:%S'),
        refresh_interval=Config.CACHE_DURATION,
        carousel_interval=Config.CAROUSEL_INTERVAL,
        logo_path=Config.LOGO_FILE_PATH,
        lessons_are_over=lessons_are_over,
        is_weekend=(time_info.day_name == "Воскресенье"),
        current_schedule_name=schedule_name
    )