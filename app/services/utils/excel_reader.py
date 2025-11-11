# app/services/utils/excel_reader.py

import pandas as pd
import logging
from typing import Optional

log = logging.getLogger(__name__)

def open_excel_file(file_path: str) -> Optional[pd.ExcelFile]:
    """
    Безопасно открывает Excel-файл и возвращает объект ExcelFile.
    Возвращает None в случае ошибки.
    """
    try:
        log.info(f"Открытие Excel-файла как объекта: {file_path}")
        xls = pd.ExcelFile(file_path, engine='calamine')
        return xls
    except FileNotFoundError:
        log.error(f"Файл не найден по пути: {file_path}")
        return None
    except Exception as e:
        log.error(f"Не удалось открыть Excel-файл '{file_path}'. Ошибка: {e}")
        return None