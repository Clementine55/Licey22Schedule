# app/services/utils/schedule_comparator.py

import logging
from typing import Dict, Any, Tuple

# --- ИЗМЕНЕНИЕ: Убираем лишние импорты, добавляем нужные ---
from app.services.parsers import schedule_parser
from app.services.utils import excel_reader

log = logging.getLogger(__name__)


def _get_lessons_as_dict(file_path: str) -> Dict[Tuple[str, str, Any], Dict[str, str]]:
    """
    Вспомогательная функция.
    Парсит Excel-файл и преобразует его в плоский словарь для легкого сравнения.
    """
    flat_lessons = {}

    # --- ИЗМЕНЕНИЕ: Используем наш excel_reader ---
    xls = excel_reader.open_excel_file(file_path)
    if not xls:
        # excel_reader уже залогировал ошибку, здесь просто выходим
        return {}

    try:
        # Используем наш основной парсер для получения "сырых" данных
        raw_lessons_by_day = schedule_parser.parse_schedule(xls, day_type_override="Обычный день")

        for day_name, lessons in raw_lessons_by_day.items():
            for lesson in lessons:
                key = (day_name, lesson.class_name, lesson.lesson_number)
                flat_lessons[key] = {
                    'subject': lesson.subject.strip() or "—",
                    'cabinet': lesson.cabinet.strip() or "—"
                }
    except Exception as e:
        log.error(f"Ошибка при парсинге файла для сравнения '{file_path}': {e}", exc_info=True)
        return {}
    finally:
        # Всегда закрываем открытый файл
        if xls:
            xls.close()

    return flat_lessons


def compare_schedules(old_file_path: str, new_file_path: str) -> Dict[str, list]:
    """
    Сравнивает два файла расписания и возвращает словарь с изменениями.
    """
    # ... весь остальной код этой функции остается без изменений ...
    # Он написан абсолютно правильно.
    log.info(f"Начинаю сравнение расписаний: '{old_file_path}' (старый) и '{new_file_path}' (новый)")

    old_lessons = _get_lessons_as_dict(old_file_path)
    new_lessons = _get_lessons_as_dict(new_file_path)

    # Если один из файлов не удалось распарсить, сравнение невозможно
    if not old_lessons or not new_lessons:
        log.warning("Один из файлов пуст или не удалось его распарсить. Сравнение отменено.")
        return {}

    old_keys = set(old_lessons.keys())
    new_keys = set(new_lessons.keys())

    # Находим общие, добавленные и удаленные слоты расписания
    common_keys = old_keys.intersection(new_keys)
    added_keys = new_keys - old_keys
    removed_keys = old_keys - new_keys

    changes = {
        'modified': [],
        'added': [],
        'removed': []
    }

    # 1. Проверяем изменения в существующих уроках
    for key in common_keys:
        old_lesson = old_lessons[key]
        new_lesson = new_lessons[key]

        # Пропускаем сравнение пустых ячеек, чтобы не засорять отчет
        if old_lesson['subject'] == '—' and new_lesson['subject'] == '—':
            continue

        if old_lesson != new_lesson:
            changes['modified'].append({
                'day': key[0],
                'class_name': key[1],
                'lesson_number': key[2],
                'old': old_lesson,
                'new': new_lesson
            })

    # 2. Находим добавленные уроки
    for key in added_keys:
        # Учитываем только если в новом расписании появился реальный урок, а не пустое место
        if new_lessons[key]['subject'] != '—':
            changes['added'].append({
                'day': key[0],
                'class_name': key[1],
                'lesson_number': key[2],
                'new': new_lessons[key]
            })

    # 3. Находим удаленные уроки
    for key in removed_keys:
        # Учитываем только если из расписания пропал реальный урок
        if old_lessons[key]['subject'] != '—':
            changes['removed'].append({
                'day': key[0],
                'class_name': key[1],
                'lesson_number': key[2],
                'old': old_lessons[key]
            })

    # Проверяем, есть ли вообще изменения
    if not any(changes.values()):
        log.info("Изменений в расписании не обнаружено.")
        return {}

    log.info(
        f"Обнаружены изменения в расписасии: {len(changes['modified'])} изм., {len(changes['added'])} доб., {len(changes['removed'])} убрано.")
    return changes