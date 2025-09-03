import time
import os
import logging
from flask import Blueprint, render_template
from datetime import datetime, timedelta, time as time_obj  # Импортируем time как time_obj
from .services import yandex_disk_client, schedule_parser, time_service
from config import Config

log = logging.getLogger(__name__)
bp = Blueprint('main', __name__)


def make_schedule_json_serializable(data):
    """
    Рекурсивно преобразует объекты datetime.time в строки, чтобы избежать ошибок JSON.
    """
    if isinstance(data, dict):
        return {k: make_schedule_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_schedule_json_serializable(i) for i in data]
    elif isinstance(data, time_obj):
        return data.strftime('%H:%M')
    else:
        return data


@bp.route('/')
def index():
    log.info("Пользователь зашел на главную страницу.")
    local_file_path = Config.LOCAL_FILE_PATH
    cache_duration_seconds = Config.CACHE_DURATION
    should_download = True
    cached_file_exists = os.path.exists(local_file_path)

    if cached_file_exists:
        file_mod_time = os.path.getmtime(local_file_path)
        if (time.time() - file_mod_time) < cache_duration_seconds:
            should_download = False
            log.info(f"Используется свежая кэшированная версия файла '{local_file_path}'.")

    if should_download:
        if cached_file_exists:
            log.info(f"Кэшированный файл '{local_file_path}' устарел. Пытаюсь обновить.")
        else:
            log.info(f"Локальный файл '{local_file_path}' отсутствует. Начинаю скачивание.")

        download_success = yandex_disk_client.download_schedule_file(local_file_path)
        if not download_success:
            if not cached_file_exists:
                log.error("КРИТИЧЕСКАЯ ОШИБКА: Не удалось скачать файл и нет кэшированной версии.")
                return render_template('error.html', message="Не удалось загрузить файл с расписанием."), 500
            else:
                log.warning("Не удалось обновить файл расписания. Будет использована устаревшая кэшированная версия.")

    full_schedule = schedule_parser.parse_schedule(local_file_path)
    if not full_schedule:
        log.error("Файл расписания пуст или не удалось его распарсить.")
        return render_template('error.html', message="Файл расписания поврежден или имеет неверный формат."), 500

    active_day_name, current_date, current_time = time_service.get_current_day_and_time()

    schedule_for_today = full_schedule.get(active_day_name)

    if schedule_for_today and current_time:
        today = datetime.today()
        current_dt = datetime.combine(today, current_time)

        filtered_landscape_view = {}
        # Используем .get() для безопасного доступа к ключу
        for grade_key, grade_data in schedule_for_today.get("landscape_view", {}).items():
            start_time = grade_data.get('first_lesson_time')
            end_time = grade_data.get('last_lesson_end_time')
            if not start_time or not end_time: continue

            start_dt = datetime.combine(today, start_time)
            end_dt = datetime.combine(today, end_time)

            show_from = start_dt - timedelta(minutes=Config.SHOW_BEFORE_START_MIN)
            show_until = end_dt + timedelta(minutes=Config.SHOW_AFTER_END_MIN)

            if show_from <= current_dt <= show_until:
                filtered_landscape_view[grade_key] = grade_data

        schedule_for_today["landscape_view"] = filtered_landscape_view

    # --- ИСПРАВЛЕНИЕ: Преобразуем данные перед отправкой в шаблон ---
    json_safe_full_schedule = make_schedule_json_serializable(full_schedule)
    json_safe_schedule_for_today = make_schedule_json_serializable(schedule_for_today)

    log.info("Расписание успешно загружено и готово к передаче на фронтенд.")

    return render_template(
        'index.html',
        full_schedule=json_safe_full_schedule,
        schedule_for_today=json_safe_schedule_for_today,
        active_day_name=active_day_name,
        current_date=current_date,
        refresh_interval=cache_duration_seconds,
        carousel_interval=Config.CAROUSEL_INTERVAL,
        logo_path=Config.LOGO_FILE_PATH
    )

