# app/services/schedule_verification.py

import pandas as pd
import logging

log = logging.getLogger(__name__)


def verify_schedule_file(file_path: str) -> bool:
    """
    Проверяет, является ли файл расписания корректным файлом Excel
    с необходимыми колонками хотя бы на одном из листов.
    Это "страж", который не пускает некорректные файлы в основной парсер.
    """
    log.info(f"Запущена проверка корректности для файла: {file_path}")

    try:
        # 1. Пытаемся прочитать файл. Если это не Excel или он поврежден,
        # pandas выбросит исключение.
        xls_dict = pd.read_excel(file_path, sheet_name=None, engine='calamine')

        if not xls_dict:
            log.error(f"Файл '{file_path}' пуст или не содержит листов. Проверка не пройдена.")
            return False

        # 2. Ищем хотя бы один подходящий лист.
        # Нам не нужно, чтобы все листы были идеальными. Достаточно одного рабочего.
        required_columns = {'Дни', 'Уроки', 'Время'}
        for sheet_name, df in xls_dict.items():
            # issubset() проверяет, что все элементы из required_columns
            # присутствуют в колонках DataFrame.
            if required_columns.issubset(df.columns):
                log.info(f"Файл '{file_path}' успешно прошел проверку. Найден подходящий лист: '{sheet_name}'.")
                return True  # Нашли то, что искали. Проверка успешна!

        # 3. Если мы прошли весь цикл, но не нашли ни одного подходящего листа.
        log.error(f"В файле '{file_path}' не найдено ни одного листа с обязательными колонками: {required_columns}. Проверка не пройдена.")
        return False

    except Exception as e:
        # Ловим любые другие ошибки при чтении файла (например, файл не Excel).
        log.error(f"Файл '{file_path}' не удалось прочитать как Excel-документ. Ошибка: {e}. Проверка не пройдена.")
        return False