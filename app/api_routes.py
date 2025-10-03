# app/api_routes.py

import logging
from flask import Blueprint, jsonify, abort
from .services import schedule_parser
from config import Config

# Создаем новый "Blueprint" специально для нашего API.
# Это как мини-приложение внутри основного.
bp = Blueprint('api', __name__, url_prefix='/api')

log = logging.getLogger(__name__)

# Та же самая функция для преобразования времени в строку,
# которую мы использовали в основном файле маршрутов.
def make_schedule_json_serializable(data):
    from datetime import time as time_obj
    if isinstance(data, dict):
        return {k: make_schedule_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_schedule_json_serializable(i) for i in data]
    elif isinstance(data, time_obj):
        return data.strftime('%H:%M')
    else:
        return data

@bp.route('/schedule/<schedule_name>')
def get_schedule(schedule_name):
    """
    Этот маршрут отдает полное расписание в формате JSON.
    """
    log.info(f"API запрос для расписания: '{schedule_name}'")

    # 1. Проверяем, существует ли такое расписание в конфиге
    if schedule_name not in Config.SCHEDULES:
        log.warning(f"API: Попытка доступа к несуществующему расписанию: '{schedule_name}'")
        # Возвращаем ошибку 404 в формате JSON
        return jsonify({"error": "Schedule not found"}), 404

    # 2. Получаем путь к локальному файлу
    local_file_path = Config.SCHEDULES[schedule_name]['local_path']

    # 3. Парсим файл
    # ВАЖНО: Мы предполагаем, что файл уже скачан и актуален,
    # так как логика скачивания остается на основной странице.
    full_schedule = schedule_parser.parse_schedule(local_file_path)

    if not full_schedule:
        log.error(f"API: Файл расписания '{schedule_name}' пуст или не может быть обработан.")
        return jsonify({"error": "Failed to parse schedule file"}), 500

    # 4. Преобразуем и отдаем данные в формате JSON
    json_safe_schedule = make_schedule_json_serializable(full_schedule)
    log.info(f"API: Расписание '{schedule_name}' успешно отправлено.")
    return jsonify(json_safe_schedule)