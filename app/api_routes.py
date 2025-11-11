# app/api_routes.py

import logging
from flask import Blueprint, jsonify

from .services.clients import time_service
from .services.core import cache_manager


bp = Blueprint('api', __name__, url_prefix='/api')
log = logging.getLogger(__name__)


@bp.route('/schedule/<schedule_name>')
def get_schedule(schedule_name):
    """Отдает полное расписание в JSON, используя кэш."""
    log.info(f"API request for schedule: '{schedule_name}'")

    # 1. Получаем все данные из кэша
    all_data = cache_manager.get_schedule_data(schedule_name)
    if all_data.get("error"):
        return jsonify({"error": "Failed to get schedule data"}), 500

    # 2. Определяем тип дня
    time_info = time_service.get_current_day_and_time()
    short_days = all_data.get("short_days", [])
    is_short_day = time_info.date_str_iso in short_days

    # 3. Выбираем нужные данные
    schedule_to_send = all_data.get("schedule_short") if is_short_day else all_data.get("schedule_normal")

    log.info(f"API: Расписание '{schedule_name}' успешно отправлено.")
    return jsonify(schedule_to_send)


@bp.route('/consultations/<schedule_name>')
def get_consultations(schedule_name):
    """Отдает расписание консультаций из кэша."""
    log.info(f"API request for consultations: '{schedule_name}'")

    all_data = cache_manager.get_schedule_data(schedule_name)
    if all_data.get("error"):
        return jsonify({"error": "Failed to get consultations data"}), 500

    consultations = all_data.get("consultations")
    log.info(f"API: Консультации для '{schedule_name}' успешно отправлены.")
    return jsonify(consultations)