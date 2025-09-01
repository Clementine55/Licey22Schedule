import re
from datetime import time


def normalize_and_get_class_name(s: str):
    """
    Проверяет, соответствует ли строка формату класса, и нормализует ее,
    добавляя пробел, если его нет (например, '5А' -> '5 А').

    Args:
      s: Входная строка для проверки.

    Returns:
      Нормализованное имя класса (str) в случае успеха, иначе None.
    """
    s = str(s).strip()

    # Паттерн 1: Проверяем слитное написание (5А, 10Б)
    # и сразу добавляем пробел
    match_no_space = re.fullmatch(r'^(10|11|[1-9])([А-Яа-яЁёa-zA-Z]{1,6})$', s)
    if match_no_space:
        num, letter = match_no_space.groups()
        return f"{num} {letter}"

    # Паттерн 2: Проверяем правильное написание с пробелом (5 А, 10 Б)
    pattern_with_space = r'^(10|11|[1-9])\s[А-Яа-яЁёa-zA-Z]{1,6}$'
    if re.fullmatch(pattern_with_space, s):
        return s

    return None  # Если ни один формат не подошел


def parse_time_str(time_str: str) -> time or None:
    match = re.match(r'(\d{1,2})[.:](\d{2})', str(time_str))
    if match:
        h, m = map(int, match.groups())
        return time(h, m)
    return None
