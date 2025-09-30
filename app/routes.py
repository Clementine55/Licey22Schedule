import time
import os
import logging
from flask import Blueprint, render_template
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


@bp.route('/')
def index():
    log.info("User accessed the main page.")
    local_file_path = Config.LOCAL_FILE_PATH
    cache_duration_seconds = Config.CACHE_DURATION
    should_download = True
    cached_file_exists = os.path.exists(local_file_path)

    if cached_file_exists:
        file_mod_time = os.path.getmtime(local_file_path)
        if (time.time() - file_mod_time) < cache_duration_seconds:
            should_download = False
            log.info(f"Using fresh cached version of the file '{local_file_path}'.")

    if should_download:
        if cached_file_exists:
            log.info(f"Cached file '{local_file_path}' is outdated. Attempting to update.")
        else:
            log.info(f"Local file '{local_file_path}' is missing. Starting download.")

        download_success = yandex_disk_client.download_schedule_file(local_file_path)
        if not download_success:
            if not cached_file_exists:
                log.error("CRITICAL ERROR: Failed to download file and no cached version is available.")
                return render_template('error.html',
                                       message="Не удалось загрузить файл с расписанием.",
                                       logo_path=Config.LOGO_FILE_PATH), 500
            else:
                log.warning("Failed to update schedule file. Using outdated cached version.")

    full_schedule = schedule_parser.parse_schedule(local_file_path)
    if not full_schedule:
        log.error("Schedule file is empty or could not be parsed.")
        return render_template('error.html',
                               message="Файл расписания поврежден или имеет неверный формат.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    active_day_name, current_date, current_time = time_service.get_current_day_and_time()

    is_weekend = active_day_name in ["Воскресенье"]

    schedule_for_today = full_schedule.get(active_day_name)
    lessons_are_over = False

    if schedule_for_today and current_time:
        # Check if there were any landscape slides to begin with
        initial_slides = schedule_for_today.get("landscape_slides", [])
        initial_lessons_existed = bool(initial_slides)

        today = datetime.today()
        current_dt = datetime.combine(today, current_time)

        active_grade_groups = []
        # Flatten the list of slides and filter each group based on time
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

                    # Keep the group if the current time is within the display window
                    if show_from <= current_dt <= show_until:
                        active_grade_groups.append(grade_data)

        # Rebuild the slide structure from the filtered (active) groups
        filtered_landscape_slides = []
        i = 0
        while i < len(active_grade_groups):
            group1_data = active_grade_groups[i]
            rows1_count = len(group1_data.get('schedule_rows', []))

            if i + 1 < len(active_grade_groups):
                group2_data = active_grade_groups[i + 1]
                rows2_count = len(group2_data.get('schedule_rows', []))

                # If total rows would be too many, put the first group on its own slide
                if rows1_count + rows2_count > 16:
                    filtered_landscape_slides.append([group1_data])
                    i += 1
                else:
                    # Otherwise, pair them up on one slide
                    filtered_landscape_slides.append([group1_data, group2_data])
                    i += 2
            else:
                # Last group, add it by itself
                filtered_landscape_slides.append([group1_data])
                i += 1

        # Update the schedule with the correctly filtered slides
        schedule_for_today["landscape_slides"] = filtered_landscape_slides

        # Set the flag if lessons existed today but are now over (filtered list is empty)
        if initial_lessons_existed and not filtered_landscape_slides:
            lessons_are_over = True

    json_safe_full_schedule = make_schedule_json_serializable(full_schedule)
    json_safe_schedule_for_today = make_schedule_json_serializable(schedule_for_today)
    current_time_str = current_time.strftime('%H:%M:%S') if current_time else '00:00:00'

    log.info("Schedule loaded successfully and is ready to be sent to the frontend.")

    return render_template(
        'index.html',
        full_schedule=json_safe_full_schedule,
        schedule_for_today=json_safe_schedule_for_today,
        active_day_name=active_day_name,
        current_date=current_date,
        current_time=current_time_str,
        refresh_interval=cache_duration_seconds,
        carousel_interval=Config.CAROUSEL_INTERVAL,
        logo_path=Config.LOGO_FILE_PATH,
        lessons_are_over=lessons_are_over,
        is_weekend=is_weekend
    )