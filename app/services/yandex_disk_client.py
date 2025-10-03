import yadisk
import requests
import logging
import os
from config import Config

from .schedule_verification import verify_schedule_file

log = logging.getLogger(__name__)


def download_schedule_file(yandex_path: str, local_path: str):
    """
    Скачивает и проверяет файл с Яндекс.Диска.
    Замена старого файла происходит только после успешной проверки.
    """
    temp_path = local_path + ".tmp"

    try:
        y = yadisk.YaDisk(token=Config.YANDEX_TOKEN)
        log.info(f"Подключаюсь к Яндекс.Диску для скачивания '{yandex_path}'...")

        # Шаг 1: Скачиваем во временный файл
        y.download(yandex_path, temp_path)
        log.info(f"Файл успешно скачан во временное хранилище: {temp_path}")

        # --- НОВЫЙ БЛОК: ВЕРИФИКАЦИЯ ФАЙЛА ---
        # Шаг 2: Проверяем скачанный временный файл перед заменой основного.
        if not verify_schedule_file(temp_path):
            log.error(f"Скачанный файл '{yandex_path}' не прошел верификацию. Обновление отменено.")
            # Возвращаем False, чтобы основная логика знала о сбое
            return False
        # --- КОНЕЦ НОВОГО БЛОКА ---

        # Шаг 3: Если проверка пройдена, атомарно заменяем старый файл новым.
        os.replace(temp_path, local_path)

        log.info(f"Файл '{yandex_path}' успешно скачан, проверен и обновлен в '{local_path}'")
        return True

    except (requests.exceptions.ConnectionError, yadisk.exceptions.YaDiskConnectionError):
        log.error("Сетевая ошибка: не удалось подключиться к серверам Яндекса.")
        return False

    except yadisk.exceptions.PathNotFoundError:
        log.error(f"Файл не найден на Диске по пути: {yandex_path}")
        return False

    except yadisk.exceptions.ForbiddenError:
        log.error(f"У вас нет доступа к файлу: {yandex_path}")
        return False

    except Exception as e:
        log.critical(f"Произошла непредвиденная ошибка при скачивании файла: {e}", exc_info=True)
        return False

    finally:
        # Шаг 4: В любом случае (успех или провал), удаляем временный файл, если он остался
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                log.error(f"Не удалось удалить временный файл {temp_path}: {e}")