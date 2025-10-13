import time
import os
import logging
from flask import Blueprint, render_template, abort, redirect, url_for
from datetime import datetime, timedelta, time as time_obj
from .services import yandex_disk_client, schedule_parser, time_service, consultation_parser
from config import Config

log = logging.getLogger(__name__)
bp = Blueprint('main', __name__)


def make_schedule_json_serializable(data):
    if isinstance(data, dict):
        return {k: make_schedule_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_schedule_json_serializable(i) for i in data]
    elif isinstance(data, time_obj):
        return data.strftime('%H:%M')
    return data


@bp.route('/')
def root():
    default_schedule_name = next(iter(Config.SCHEDULES))
    return redirect(url_for('main.index', schedule_name=default_schedule_name))


@bp.route('/<schedule_name>')
def index(schedule_name):
    if schedule_name not in Config.SCHEDULES:
        abort(404)

    schedule_config = Config.SCHEDULES[schedule_name]
    yandex_file_path, local_file_path = schedule_config['yandex_path'], schedule_config['local_path']
    cache_duration = Config.CACHE_DURATION

    if not os.path.exists(local_file_path) or (time.time() - os.path.getmtime(local_file_path)) > cache_duration:
        yandex_disk_client.download_schedule_file(yandex_file_path, local_file_path)

    if not os.path.exists(local_file_path):
        return render_template('error.html', message=f"Could not load schedule file '{schedule_name}'.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    full_schedule = schedule_parser.parse_schedule(local_file_path)
    all_consultations = consultation_parser.parse_consultations(local_file_path)
    if not full_schedule:
        return render_template('error.html', message="Schedule file is damaged or has an incorrect format.",
                               logo_path=Config.LOGO_FILE_PATH), 500

    active_day_name, current_date, current_time = time_service.get_current_day_and_time()
    consultations_for_today = all_consultations.get(active_day_name, [])
    schedule_for_today = full_schedule.get(active_day_name)
    lessons_are_over = False

    if schedule_for_today and current_time:
        initial_slides = schedule_for_today.get("landscape_slides", [])
        initial_lessons_existed = bool(initial_slides)
        today, current_dt = datetime.today(), datetime.combine(datetime.today(), current_time)

        active_grade_groups = []
        if initial_lessons_existed:
            for slide in initial_slides:
                for grade_data in slide:
                    start_dt = datetime.combine(today, grade_data['first_lesson_time']) - timedelta(
                        minutes=Config.SHOW_BEFORE_START_MIN)
                    end_dt = datetime.combine(today, grade_data['last_lesson_end_time']) + timedelta(
                        minutes=Config.SHOW_AFTER_END_MIN)
                    if start_dt <= current_dt <= end_dt:
                        active_grade_groups.append(grade_data)

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
        if initial_lessons_existed and not filtered_slides:
            lessons_are_over = True

    return render_template(
        'index.html',
        schedule_for_today=make_schedule_json_serializable(schedule_for_today),
        consultations_for_today=consultations_for_today,
        active_day_name=active_day_name,
        current_date=current_date,
        current_time=current_time.strftime('%H:%M:%S') if current_time else '00:00:00',
        refresh_interval=cache_duration,
        carousel_interval=Config.CAROUSEL_INTERVAL,
        logo_path=Config.LOGO_FILE_PATH,
        lessons_are_over=lessons_are_over,
        is_weekend=(active_day_name == "Воскресенье"),
        current_schedule_name=schedule_name
    )

