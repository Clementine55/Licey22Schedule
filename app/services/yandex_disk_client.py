import yadisk
import requests
import logging
import os
from config import Config

log = logging.getLogger(__name__)


def download_schedule_file(local_path):
    """
    Скачивает файл во временное место, чтобы избежать повреждения основного файла
    при сбое сети.
    """
    temp_path = local_path + ".tmp"

    try:
        y = yadisk.YaDisk(token=Config.YANDEX_TOKEN)
        log.info("Подключаюсь к Яндекс.Диску для скачивания файла...")

        # Шаг 1: Скачиваем во временный файл
        y.download(Config.YANDEX_FILE_PATH, temp_path)

        # Шаг 2: Если скачивание успешно, переименовываем временный файл в основной
        os.rename(temp_path, local_path)

        log.info(f"Файл '{Config.YANDEX_FILE_PATH}' успешно скачан и обновлен в '{local_path}'")
        return True

    except (requests.exceptions.ConnectionError, yadisk.exceptions.YaDiskConnectionError):
        log.error("Сетевая ошибка: не удалось подключиться к серверам Яндекса. Проверьте интернет-соединение.")
        return False

    except yadisk.exceptions.PathNotFoundError:
        log.error(f"Файл не найден на Диске по пути: {Config.YANDEX_FILE_PATH}")
        return False

    except yadisk.exceptions.ForbiddenError:
        log.error(f"У вас нет доступа к файлу: {Config.YANDEX_FILE_PATH}")
        return False

    except Exception as e:
        log.critical(f"Произошла непредвиденная ошибка при скачивании файла: {e}", exc_info=True)
        return False

    finally:
        # Шаг 3: В любом случае (успех или провал), удаляем временный файл, если он остался
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                log.error(f"Не удалось удалить временный файл {temp_path}: {e}")

