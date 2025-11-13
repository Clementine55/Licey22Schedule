# app/services/utils/enums.py

from enum import Enum, auto

class DayType(Enum):
    """Определяет тип учебного дня (обычный или сокращенный)."""
    NORMAL = auto()
    SHORT = auto()

class Shift(Enum):
    """Определяет тип смены (первая или вторая)."""
    FIRST = auto()
    SECOND = auto()