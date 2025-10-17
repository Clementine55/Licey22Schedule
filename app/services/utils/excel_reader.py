import pandas as pd
import logging
from typing import Dict, List

log = logging.getLogger(__name__)

def load_excel_sheets(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Безопасно загружает все листы из Excel-файла.
    Возвращает словарь {имя_листа: DataFrame} или пустой словарь при ошибке.
    """
    try:
        log.info(f"Чтение Excel-файла: {file_path}")
        # Читаем с обычным, однострочным заголовком по умолчанию
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')
        if not xls_dict:
            log.error(f"Файл '{file_path}' пуст или не содержит листов.")
            return {}
        return xls_dict
    except FileNotFoundError:
        log.error(f"Файл не найден по пути: {file_path}")
        return {}
    except Exception as e:
        log.error(f"Не удалось прочитать Excel-файл '{file_path}'. Ошибка: {e}")
        return {}

def filter_sheets_by_keyword(
    sheets_dict: Dict[str, pd.DataFrame],
    keyword: str
) -> Dict[str, pd.DataFrame]:
    # ... (эта функция остается без изменений) ...
    found_sheets = {}
    keyword_lower = keyword.lower()
    for sheet_name, df in sheets_dict.items():
        if keyword_lower in str(sheet_name).lower():
            found_sheets[sheet_name] = df
    return found_sheets