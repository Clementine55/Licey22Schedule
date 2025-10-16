# app/services/short_day_parser.py (Финальная, объединенная версия)

import pandas as pd
import logging
from typing import Set

log = logging.getLogger(__name__)


# --- Эта функция теперь "приватная", для внутреннего использования ---
def _get_short_days_from_file(file_path: str) -> Set[str]:
    """
    Внутренняя функция для чтения дат коротких дней из файла.
    Возвращает множество строк в формате 'ГГГГ-ММ-ДД'.
    """
    try:
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')

        sheet_name = next((s for s in xls_dict.keys() if 'сокращенные' in s.lower() or 'сокращ' in s.lower()), None)
        if not sheet_name:
            # Это не ошибка, а нормальная ситуация
            return set()

        df = xls_dict[sheet_name]
        if 'Дата' not in df.columns:
            log.warning(f"На листе '{sheet_name}' не найдена колонка 'Дата'.")
            return set()

        dates = set()
        for date_val in df['Дата'].dropna():
            try:
                # dayfirst=True правильно распознает формат ДД.ММ.ГГГГ
                parsed_date = pd.to_datetime(date_val, dayfirst=True)
                dates.add(parsed_date.strftime('%Y-%m-%d'))
            except (ValueError, TypeError):
                log.warning(f"Не удалось распознать дату '{date_val}' на листе '{sheet_name}'.")

        return dates

    except Exception as e:
        log.error(f"Критическая ошибка при чтении дат коротких дней из файла '{file_path}': {e}")
        return set()


# --- ЕДИНСТВЕННАЯ ПУБЛИЧНАЯ ФУНКЦИЯ, КОТОРУЮ МЫ БУДЕМ ВЫЗЫВАТЬ ---
def is_today_a_short_day(file_path: str, current_date_iso: str) -> bool:
    """
    Главная функция сервиса. Читает файл и проверяет, является ли текущий день коротким.
    Возвращает True, если день короткий, иначе False.
    """
    short_days_list = _get_short_days_from_file(file_path)
    return current_date_iso in short_days_list