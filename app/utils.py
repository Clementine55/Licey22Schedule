# app/utils.py

from datetime import time as time_obj
from dataclasses import is_dataclass, asdict


def make_json_serializable(data):
    """
    Рекурсивно преобразует объекты, которые не сериализуются в JSON,
    в подходящий формат (строки, словари, списки).
    """
    # Этот блок - ключ к решению проблемы. Он должен быть первым.
    if is_dataclass(data):
        # Превращаем дата-класс в словарь и снова пропускаем через эту же функцию,
        # чтобы обработать любые вложенные объекты (например, time)
        return make_json_serializable(asdict(data))

    # Остальные проверки остаются как были
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [make_json_serializable(i) for i in data]
    if isinstance(data, time_obj):
        return data.strftime('%H:%M')

    return data