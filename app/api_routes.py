import logging
from flask import Blueprint, jsonify, abort
from .services import schedule_parser, consultation_parser
from config import Config
from datetime import time as time_obj

bp = Blueprint('api', __name__, url_prefix='/api')
log = logging.getLogger(__name__)

def make_schedule_json_serializable(data):
    if isinstance(data, dict):
        return {k: make_schedule_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_schedule_json_serializable(i) for i in data]
    elif isinstance(data, time_obj):
        return data.strftime('%H:%M')
    return data

@bp.route('/schedule/<schedule_name>')
def get_schedule(schedule_name):
    """Provides the full schedule as JSON."""
    log.info(f"API request for schedule: '{schedule_name}'")
    if schedule_name not in Config.SCHEDULES:
        return jsonify({"error": "Schedule not found"}), 404

    local_file_path = Config.SCHEDULES[schedule_name]['local_path']
    full_schedule = schedule_parser.parse_schedule(local_file_path)

    if not full_schedule:
        log.error(f"API: Schedule file '{schedule_name}' is empty or unprocessable.")
        return jsonify({"error": "Failed to parse schedule file"}), 500

    json_safe_schedule = make_schedule_json_serializable(full_schedule)
    log.info(f"API: Schedule '{schedule_name}' sent successfully.")
    return jsonify(json_safe_schedule)

@bp.route('/consultations/<schedule_name>')
def get_consultations(schedule_name):
    """Provides the consultation schedule as JSON."""
    log.info(f"API request for consultations: '{schedule_name}'")
    if schedule_name not in Config.SCHEDULES:
        return jsonify({"error": "Schedule not found"}), 404

    local_file_path = Config.SCHEDULES[schedule_name]['local_path']
    consultations = consultation_parser.parse_consultations(local_file_path)
    log.info(f"API: Consultations for '{schedule_name}' sent successfully.")
    return jsonify(consultations)
