# app/services/schedule_verification.py

import logging

log = logging.getLogger(__name__)


def verify_schedule_file(file_path: str) -> bool:
    """
    Проверяет файл расписания на корректность.

    На данный момент это заглушка, которая всегда возвращает True.
    В будущем здесь будут проверки:
    - Является ли файл действительным XLSX.
    - Есть ли в нем необходимые листы и колонки.
    - Не является ли файл пустым.

    :param file_path: Путь к проверяемому файлу (обычно временный .tmp файл).
    :return: True, если файл прошел проверку, иначе False.
    """
    log.info(f"Запущена проверка корректности для файла: {file_path}")

    # TODO: Добавить реальные условия проверки файла
    is_valid = True

    if not is_valid:
        log.error(f"Файл '{file_path}' не прошел проверку на корректность.")
        return False

    log.info(f"Файл '{file_path}' успешно прошел проверку.")
    return True