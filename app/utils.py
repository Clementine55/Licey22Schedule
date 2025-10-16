# app/utils.py

from datetime import time as time_obj

def make_json_serializable(data):
    """
    Рекурсивно преобразует объекты, которые не сериализуются в JSON (например, time),
    в строковый формат.
    """
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [make_json_serializable(i) for i in data]
    if isinstance(data, time_obj):
        return data.strftime('%H:%M')
    return data