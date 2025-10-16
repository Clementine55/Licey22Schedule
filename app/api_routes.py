# app/api_routes.py (Финальная, "умная" версия)

import logging
from flask import Blueprint, jsonify
from config import Config
from .utils import make_json_serializable

# Импортируем все необходимые сервисы, как в routes.py
from .services import (
    schedule_parser,
    consultation_parser,
    time_service,
    short_day_parser
)

bp = Blueprint('api', __name__, url_prefix='/api')
log = logging.getLogger(__name__)


@bp.route('/schedule/<schedule_name>')
def get_schedule(schedule_name):
    """Отдает полное расписание в формате JSON, учитывая тип текущего дня."""
    log.info(f"API request for schedule: '{schedule_name}'")
    if schedule_name not in Config.SCHEDULES:
        return jsonify({"error": "Schedule not found"}), 404

    local_file_path = Config.SCHEDULES[schedule_name]['local_path']

    # --- ДОБАВЛЯЕМ ЛОГИКУ ПРОВЕРКИ ТИПА ДНЯ (как в routes.py) ---
    time_info = time_service.get_current_day_and_time()
    is_short_day = short_day_parser.is_today_a_short_day(local_file_path, time_info.date_str_iso)
    current_day_type = "Короткий день" if is_short_day else "Обычный день"
    # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

    # Передаем тип дня в парсер
    full_schedule = schedule_parser.parse_schedule(local_file_path, day_type_override=current_day_type)

    if not full_schedule:
        log.error(f"API: Файл расписания '{schedule_name}' пуст или не может быть обработан.")
        return jsonify({"error": "Failed to parse schedule file"}), 500

    json_safe_schedule = make_json_serializable(full_schedule)
    log.info(f"API: Расписание '{schedule_name}' успешно отправлено.")
    return jsonify(json_safe_schedule)


@bp.route('/consultations/<schedule_name>')
def get_consultations(schedule_name):
    """Отдает расписание консультаций в формате JSON, учитывая тип текущего дня."""
    log.info(f"API request for consultations: '{schedule_name}'")
    if schedule_name not in Config.SCHEDULES:
        return jsonify({"error": "Schedule not found"}), 404

    local_file_path = Config.SCHEDULES[schedule_name]['local_path']

    # --- ДОБАВЛЯЕМ ТУ ЖЕ САМУЮ ЛОГИКУ И СЮДА ---
    time_info = time_service.get_current_day_and_time()
    is_short_day = short_day_parser.is_today_a_short_day(local_file_path, time_info.date_str_iso)
    current_day_type = "Короткий день" if is_short_day else "Обычный день"
    # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

    # Передаем тип дня в парсер консультаций
    consultations = consultation_parser.parse_consultations(local_file_path, day_type_override=current_day_type)

    log.info(f"API: Консультации для '{schedule_name}' успешно отправлены.")
    return jsonify(make_json_serializable(consultations))