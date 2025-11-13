# app/services/utils/schedule_verification.py

import logging
import re
import pandas as pd

from . import excel_reader


log = logging.getLogger(__name__)


SHEET_CONTRACTS = {
    "Сокращенные дни": {
        "pattern": r'сокращ',
        "columns": {'дата'}
    },
    "Консультации": {
        "pattern": r'консультац',
        "columns": {'учитель', 'фио'}
    },
    "Начальная школа": {
        "pattern": r'нач[.\s]*школа',
        "columns": {'дни', 'уроки', 'время'}
    },
    "Основное расписание": {
        "pattern": r'\d+-\d+\s*класс\s*\(\s*\d\s*смена\s*\)',
        "columns": {'дни', 'уроки', 'время'}
    }
}


def verify_schedule_file(file_path: str) -> bool:
    """
    Выполняет строгую проверку Excel-файла на наличие всех обязательных
    типов листов с правильными колонками.
    """
    log.info(f"Запущена строгая проверка структуры для файла: {file_path}")

    xls = excel_reader.open_excel_file(file_path)
    if not xls:
        return False

    try:
        sheet_names = xls.sheet_names
        if not sheet_names:
            log.error(f"Файл '{file_path}' пуст. Проверка не пройдена.")
            return False

        # Копируем ключи контракта. По мере нахождения будем их удалять.
        requirements_to_find = set(SHEET_CONTRACTS.keys())

        # Проходим по каждому листу ОДИН РАЗ
        for sheet_name in sheet_names:
            sheet_type_found = None

            # 1. Определяем тип текущего листа
            for req_name, contract in SHEET_CONTRACTS.items():
                if req_name in requirements_to_find and re.search(contract['pattern'], sheet_name, re.IGNORECASE):
                    sheet_type_found = req_name
                    break  # Тип нашли, выходим из внутреннего цикла

            if not sheet_type_found:
                continue  # Этот лист нас не интересует, берем следующий

            # 2. Выполняем проверку колонок в зависимости от типа листа
            is_valid = False
            contract = SHEET_CONTRACTS[sheet_type_found]

            try:
                if sheet_type_found == "Консультации":
                    # --- ОСОБАЯ ПРОВЕРКА ДЛЯ КОНСУЛЬТАЦИЙ ---
                    df = pd.read_excel(xls, sheet_name=sheet_name, header=[0, 1])
                    # Превращаем двухуровневые заголовки в плоскую строку для поиска
                    flat_columns = {" ".join(map(str, col)).lower() for col in df.columns}
                    # Проверяем, есть ли хотя бы одна колонка, содержащая 'учитель' или 'фио'
                    if any('учитель' in col or 'фио' in col for col in flat_columns):
                        is_valid = True
                else:
                    # --- СТАНДАРТНАЯ ПРОВЕРКА ДЛЯ ОСТАЛЬНЫХ ЛИСТОВ ---
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    sheet_columns = {str(col).lower() for col in df.columns}
                    if contract['columns'].issubset(sheet_columns):
                        is_valid = True
            except Exception as e:
                log.warning(f"Не удалось прочитать или проверить лист '{sheet_name}'. Ошибка: {e}. Пропускаем.")
                continue  # Переходим к следующему листу

            # 3. Если лист прошел проверку, отмечаем требование как выполненное
            if is_valid:
                requirements_to_find.remove(sheet_type_found)
                log.info(f"  [✓] Найден и проверен лист типа '{sheet_type_found}' (лист: '{sheet_name}')")

            # Если мы уже нашли все, что искали, можно досрочно выйти
            if not requirements_to_find:
                break

        # --- ФИНАЛЬНАЯ ПРОВЕРКА ---
        if not requirements_to_find:
            log.info(f"Файл '{file_path}' успешно прошел проверку. Все обязательные типы листов найдены.")
            return True
        else:
            log.error(
                f"Проверка файла '{file_path}' не пройдена. Не найдены или некорректны листы: {', '.join(requirements_to_find)}.")
            return False

    except Exception as e:
        log.error(f"Произошла непредвиденная ошибка во время верификации файла '{file_path}': {e}", exc_info=True)
        return False
    finally:
        if xls:
            xls.close()