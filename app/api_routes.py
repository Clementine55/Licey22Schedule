# app/api_routes.py

import logging
from flask import Blueprint, jsonify

from .services.clients import time_service
from .services.core import cache_manager


bp = Blueprint('api', __name__, url_prefix='/api')
log = logging.getLogger(__name__)


@bp.route('/schedule/<schedule_name>')
def get_schedule(schedule_name):
    """Отдает актуальное на сегодня расписание в JSON."""
    log.info(f"API request for schedule: '{schedule_name}'")

    all_data = cache_manager.get_schedule_data(schedule_name)
    if all_data.get("error"):
        return jsonify({"error": "Failed to get schedule data"}), 500

    schedule_to_send = all_data.get("schedule")

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