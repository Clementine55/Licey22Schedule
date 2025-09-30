import re
from datetime import time


def is_valid_class_name(s: str) -> bool:
    """
    Проверяет, соответствует ли строка формату имени класса.
    Требует, чтобы имя начиналось с цифры (1-11), за которой следует хотя бы одна буква.
    Допускает сложные имена, например '11ИП(наука)'.
    """
    s = str(s).strip()
    # Паттерн: начинается с 1-11, далее опциональный пробел,
    # затем должна идти буква, а после неё могут быть любые символы.
    pattern = r'^(10|11|[1-9])\s?[А-Яа-яЁёA-Za-z].*$'
    if re.fullmatch(pattern, s):
        return True
    return False


def normalize_class_name(s: str) -> str:
    """
    Нормализует имя класса, добавляя пробел между цифрой и остальной частью, если его нет.
    Пример: '11ИП(наука)' -> '11 ИП(наука)'
    """
    s = str(s).strip()
    # Ищем слитное написание, чтобы добавить пробел
    match = re.match(r'^(10|11|[1-9])([А-Яа-яЁёA-Za-z].*)$', s)
    if match:
        num, rest = match.groups()
        return f"{num} {rest}"

    # Если пробел уже есть, просто возвращаем строку как есть
    if re.match(r'^(10|11|[1-9])\s.*$', s):
        return s

    return s  # Возвращаем как есть, если формат неожиданный


def parse_time_str(time_str: str) -> time or None:
    """Парсит время из строки."""
    match = re.match(r'(\d{1,2})[.:](\d{2})', str(time_str))
    if match:
        h, m = map(int, match.groups())
        if 0 <= h < 24 and 0 <= m < 60:
            return time(h, m)
    return None
