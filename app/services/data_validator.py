import re
from datetime import time


def is_valid_class_name(s: str) -> bool:
    """
    Проверяет, соответствует ли строка формату имени класса.
    Возвращает True, если формат верный (например, '5А' или '5 А'), иначе False.
    """
    s = str(s).strip()

    # Паттерн для слитного написания (5А, 10БАС)
    pattern_no_space = r'^(10|11|[1-9])([А-Яа-яЁёa-zA-Z]{1,6})$'
    # Паттерн для написания с пробелом (5 А, 10 БАС)
    # ИСПРАВЛЕНИЕ: Убран лишний обратный слэш. Было r'...\\s...', стало r'...\s...'
    pattern_with_space = r'^(10|11|[1-9])\s[А-Яа-яЁёa-zA-Z]{1,6}$'

    if re.fullmatch(pattern_no_space, s) or re.fullmatch(pattern_with_space, s):
        return True

    return False


def normalize_class_name(s: str) -> str:
    """
    Нормализует имя класса, добавляя пробел между цифрой и буквами, если его нет.
    Предполагается, что строка уже прошла проверку is_valid_class_name.
    """
    s = str(s).strip()

    # Ищем слитное написание, чтобы добавить пробел
    match_no_space = re.fullmatch(r'^(10|11|[1-9])([А-Яа-яЁёa-zA-Z]{1,6})$', s)
    if match_no_space:
        num, letter = match_no_space.groups()
        return f"{num} {letter.upper()}"  # Также приводим литеры к верхнему регистру для единообразия

    # Если пробел уже есть, просто приводим литеры к верхнему регистру
    match_with_space = re.fullmatch(r'^(10|11|[1-9])\s([А-Яа-яЁёa-zA-Z]{1,6})$', s)
    if match_with_space:
        num, letter = match_with_space.groups()
        return f"{num} {letter.upper()}"

    return s  # Возвращаем как есть, если формат неожиданный


def parse_time_str(time_str: str) -> time or None:
    """Парсит время из строки."""
    match = re.match(r'(\d{1,2})[.:](\d{2})', str(time_str))
    if match:
        h, m = map(int, match.groups())
        if 0 <= h < 24 and 0 <= m < 60:
            return time(h, m)
    return None
