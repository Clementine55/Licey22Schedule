# app/services/short_day_parser.py (Финальная, объединенная версия)

import pandas as pd
import logging
from typing import Set

from ..utils.excel_reader import load_excel_sheets, filter_sheets_by_keyword


log = logging.getLogger(__name__)


# --- Эта функция теперь "приватная", для внутреннего использования ---
def _get_short_days_from_file(xls: pd.ExcelFile) -> Set[str]:
    """
    Внутренняя функция для чтения дат коротких дней из файла.
    """

    sheet_name = next((s for s in xls.sheet_names if 'сокращ' in s.lower()), None)
    df = pd.read_excel(xls, sheet_name=sheet_name)
    # --> КОНЕЦ ЗАМЕНЫ

    if 'Дата' not in df.columns:
        log.warning(f"На листе '{sheet_name}' не найдена колонка 'Дата'.")
        return set()

    dates = set()
    for date_val in df['Дата'].dropna():
        try:
            parsed_date = pd.to_datetime(date_val, dayfirst=True)
            dates.add(parsed_date.strftime('%Y-%m-%d'))
        except (ValueError, TypeError):
            log.warning(f"Не удалось распознать дату '{date_val}' на листе '{sheet_name}'.")

    return dates


# --- ЕДИНСТВЕННАЯ ПУБЛИЧНАЯ ФУНКЦИЯ, КОТОРУЮ МЫ БУДЕМ ВЫЗЫВАТЬ ---
def is_today_a_short_day(file_path: str, current_date_iso: str) -> bool:
    """
    Главная функция сервиса. Читает файл и проверяет, является ли текущий день коротким.
    Возвращает True, если день короткий, иначе False.
    """
    short_days_list = _get_short_days_from_file(file_path)
    return current_date_iso in short_days_list