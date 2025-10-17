# app/services/cache_manager.py

import os
import json
import time
import logging
from threading import Lock
import pandas as pd
from config import Config

from ..parsers import schedule_parser, consultation_parser, _portrait_builder, _landscape_builder, short_day_parser
from ..clients import yandex_disk_client
from app.utils import make_json_serializable

log = logging.getLogger(__name__)

# Глобальный замок, чтобы разные потоки в одном воркере не мешали друг другу
thread_lock = Lock()


def get_schedule_data(schedule_name: str) -> dict:
    """
    Главная функция. Получает расписание из кэша или запускает его обновление.
    """
    if schedule_name not in Config.SCHEDULES:
        return {"error": "Schedule not found"}

    cache_file = f"data/{schedule_name}_cache.json"
    lock_file = f"data/{schedule_name}_cache.lock"

    # Проверяем, не пора ли обновить кэш
    try:
        is_cache_stale = not os.path.exists(cache_file) or \
                         (time.time() - os.path.getmtime(cache_file)) > Config.CACHE_DURATION
    except FileNotFoundError:
        is_cache_stale = True

    if is_cache_stale:
        log.warning(f"Кэш для '{schedule_name}' устарел или отсутствует. Попытка обновления...")
        # Используем "замок", чтобы только один процесс/поток обновлял кэш
        with thread_lock:
            # Двойная проверка, вдруг другой поток уже обновил кэш, пока мы ждали замок
            if not os.path.exists(lock_file):
                try:
                    # Создаем lock-файл, чтобы другие процессы знали, что мы работаем
                    open(lock_file, 'w').close()
                    log.info(f"Lock acquired by process {os.getpid()}. Updating cache for '{schedule_name}'.")
                    _update_cache_file(schedule_name, cache_file)
                finally:
                    # Обязательно убираем замок, даже если была ошибка
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        log.info(f"Lock released by process {os.getpid()}.")
            else:
                log.info(f"Cache for '{schedule_name}' is being updated by another process. Waiting...")
                # Ждем немного, пока другой процесс закончит
                time.sleep(5)

                # Читаем свежие данные из кэша
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            log.info(f"Загрузка данных для '{schedule_name}' из файла кэша.")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log.error(f"Не удалось прочитать файл кэша для '{schedule_name}'. Возможно, первая загрузка еще не завершена.")
        # В крайнем случае, парсим файл напрямую, чтобы не отдавать ошибку
        return _parse_all_data(schedule_name)


def _update_cache_file(schedule_name: str, cache_file: str):
    """
    Внутренняя функция для скачивания, парсинга и сохранения данных в кэш.
    """
    # 1. Скачиваем актуальный файл с Яндекс.Диска
    schedule_config = Config.SCHEDULES[schedule_name]
    yandex_path = schedule_config['yandex_path']
    local_path = schedule_config['local_path']

    download_success = yandex_disk_client.download_schedule_file(yandex_path, local_path)
    if not download_success and not os.path.exists(local_path):
        log.critical(f"Не удалось ни скачать, ни найти локальный файл для '{schedule_name}'. Обновление кэша отменено.")
        return

    # 2. Парсим все данные
    log.info(f"Парсинг всех данных для '{schedule_name}'...")
    all_data = _parse_all_data(schedule_name)

    # 3. Атомарно сохраняем в JSON
    temp_cache_file = cache_file + ".tmp"
    with open(temp_cache_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    os.replace(temp_cache_file, cache_file)
    log.info(f"Кэш для '{schedule_name}' успешно обновлен.")


def _parse_all_data(schedule_name: str) -> dict:
    """Парсит и уроки, и консультации, собирая финальную структуру для кэша."""
    local_path = Config.SCHEDULES[schedule_name]['local_path']
    if not os.path.exists(local_path):
        return {"error": "Local schedule file not found"}

    # --- ИЗМЕНЕНИЕ: ЛОГИКА СБОРКИ ---

    log.info(f"Открываем файл '{local_path}' ОДИН РАЗ для всех парсеров.")
    try:
        xls = pd.ExcelFile(local_path, engine='calamine')
    except Exception as e:
        log.error(f"Не удалось открыть Excel файл: {e}")
        return {"error": f"Failed to open Excel file: {e}"}

    # Передаем ОТКРЫТЫЙ ФАЙЛ в парсеры
    raw_lessons_normal = schedule_parser.parse_schedule(xls, day_type_override="Обычный день")
    raw_lessons_short = schedule_parser.parse_schedule(xls, day_type_override="Короткий день")
    consultations = consultation_parser.parse_consultations(xls)
    short_days_list = short_day_parser._get_short_days_from_file(xls)

    # 3. Собираем финальные структуры данных, как они были раньше
    schedule_normal = {}
    schedule_short = {}
    days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

    for day in days_order:
        daily_lessons_normal = raw_lessons_normal.get(day, [])
        schedule_normal[day] = {
            "portrait_view": _portrait_builder.build_portrait_view(daily_lessons_normal),
            "landscape_slides": _landscape_builder.build_landscape_view(daily_lessons_normal)
        }

        daily_lessons_short = raw_lessons_short.get(day, [])
        schedule_short[day] = {
            "portrait_view": _portrait_builder.build_portrait_view(daily_lessons_short),
            "landscape_slides": _landscape_builder.build_landscape_view(daily_lessons_short)
        }

    return make_json_serializable({
        "schedule_normal": schedule_normal,
        "schedule_short": schedule_short,
        "consultations": consultations,
        "short_days": list(short_days_list)
    })