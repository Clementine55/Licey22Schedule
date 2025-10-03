import time
import os
import logging
from flask import Blueprint, render_template, abort, redirect, url_for
from datetime import datetime, timedelta, time as time_obj
from .services import yandex_disk_client, schedule_parser, time_service
from config import Config

log = logging.getLogger(__name__)
bp = Blueprint('main', __name__)


def make_schedule_json_serializable(data):
    """
    Recursively converts datetime.time objects to strings to avoid JSON errors.
    """
    if isinstance(data, dict):
        return {k: make_schedule_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_schedule_json_serializable(i) for i in data]
    elif isinstance(data, time_obj):
        return data.strftime('%H:%M')
    else:
        return data

# НОВЫЙ МАРШРУТ: перенаправляет с главной страницы на первое расписание из списка
@bp.route('/')
def root():
    # Получаем первый ключ из словаря расписаний (например, 'sovietskaya')
    default_schedule_name = next(iter(Config.SCHEDULES))
    # Перенаправляем на страницу этого расписания
    return redirect(url_for('main.index', schedule_name=default_schedule_name))


# ИЗМЕНЕННЫЙ МАРШРУТ: теперь он динамический
@bp.route('/<schedule_name>')
def index(schedule_name):
    log.info(f"Пользователь запросил расписание '{schedule_name}'.")

    # 1. Проверяем, существует ли такое расписание в конфиге
    if schedule_name not in Config.SCHEDULES:
        log.warning(f"Попытка доступа к несуществующему расписанию: '{schedule_name}'")
        abort(404)  # Если нет - отдаем ошибку 404

    # 2. Получаем пути для запрошенного расписания
    schedule_config = Config.SCHEDULES[schedule_name]
    yandex_file_path = schedule_config['yandex_path']
    local_file_path = schedule_config['local_path']

    # --- Дальнейшая логика остается почти без изменений, но использует полученные пути ---
    cache_duration_seconds = Config.CACHE_DURATION
    should_download = True
    cached_file_exists = os.path.exists(local_file_path)

    if cached_file_exists:
        file_mod_time = os.path.getmtime(local_file_path)
        if (time.time() - file_mod_time) < cache_duration_seconds:
            should_download = False
            log.info(f"Используется свежая кэш-версия файла '{local_file_path}'.")

    if should_download:
        if cached_file_exists:
            log.info(f"Кэш-файл '{local_file_path}' устарел. Попытка обновить.")
        else:
            log.info(f"Локальный файл '{local_file_path}' отсутствует. Начинаю загрузку.")

        # 3. Вызываем функцию скачивания с правильными путями
        download_success = yandex_disk_client.download_schedule_file(yandex_file_path, local_file_path)
        if not download_success:
            if not cached_file_exists:
                log.error("КРИТИЧЕСКАЯ ОШИБКА: Не удалось скачать файл, кэш-версия отсутствует.")
                return render_template('error.html',
                                       message=f"Не удалось загрузить файл расписания '{schedule_name}'.",
                                       logo_path=Config.LOGO_FILE_PATH), 500
            else:
                log.warning("Не удалось обновить файл расписания. Используется устаревшая кэш-версия.")

    full_schedule = schedule_parser.parse_schedule(local_file_path)
    if not full_schedule:
        log.error("Файл расписания пуст или не может быть обработан.")
        return render_template('error.html',
                               message="Файл расписания поврежден или имеет неверный формат.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    # ... остальная часть функции без изменений ...
    active_day_name, current_date, current_time = time_service.get_current_day_and_time()

    is_weekend = active_day_name in ["Воскресенье"]

    schedule_for_today = full_schedule.get(active_day_name)
    lessons_are_over = False

    if schedule_for_today and current_time:
        initial_slides = schedule_for_today.get("landscape_slides", [])
        initial_lessons_existed = bool(initial_slides)
        today = datetime.today()
        current_dt = datetime.combine(today, current_time)
        active_grade_groups = []

        if initial_lessons_existed:
            for slide in initial_slides:
                for grade_data in slide:
                    start_time = grade_data.get('first_lesson_time')
                    end_time = grade_data.get('last_lesson_end_time')
                    if not start_time or not end_time:
                        continue
                    start_dt = datetime.combine(today, start_time)
                    end_dt = datetime.combine(today, end_time)
                    show_from = start_dt - timedelta(minutes=Config.SHOW_BEFORE_START_MIN)
                    show_until = end_dt + timedelta(minutes=Config.SHOW_AFTER_END_MIN)
                    if show_from <= current_dt <= show_until:
                        active_grade_groups.append(grade_data)

        filtered_landscape_slides = []
        i = 0
        while i < len(active_grade_groups):
            group1_data = active_grade_groups[i]
            rows1_count = len(group1_data.get('schedule_rows', []))
            if i + 1 < len(active_grade_groups):
                group2_data = active_grade_groups[i + 1]
                rows2_count = len(group2_data.get('schedule_rows', []))
                if rows1_count + rows2_count > 16:
                    filtered_landscape_slides.append([group1_data])
                    i += 1
                else:
                    filtered_landscape_slides.append([group1_data, group2_data])
                    i += 2
            else:
                filtered_landscape_slides.append([group1_data])
                i += 1
        schedule_for_today["landscape_slides"] = filtered_landscape_slides
        if initial_lessons_existed and not filtered_landscape_slides:
            lessons_are_over = True

    json_safe_schedule_for_today = make_schedule_json_serializable(schedule_for_today)
    current_time_str = current_time.strftime('%H:%M:%S') if current_time else '00:00:00'

    current_schedule_name = schedule_name

    log.info(f"Расписание '{schedule_name}' успешно загружено и готово к отправке.")
    return render_template(
        'index.html',
        schedule_for_today=json_safe_schedule_for_today,
        active_day_name=active_day_name,
        current_date=current_date,
        current_time=current_time_str,
        refresh_interval=cache_duration_seconds,
        carousel_interval=Config.CAROUSEL_INTERVAL,
        logo_path=Config.LOGO_FILE_PATH,
        lessons_are_over=lessons_are_over,
        is_weekend=is_weekend,
        current_schedule_name = current_schedule_name
    )