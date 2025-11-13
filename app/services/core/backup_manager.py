# app/services/core/backup_manager.py

import os
import logging
from datetime import datetime, timedelta
import re
import shutil
from config import Config


log = logging.getLogger(__name__)


def create_backup(schedule_name: str, file_to_backup_path: str) -> bool:
    """
    Создает бэкап файла в подпапке с именем расписания.
    """
    if not os.path.exists(file_to_backup_path):
        log.info(f"Файл для бэкапа не существует: '{file_to_backup_path}'. Бэкап не требуется.")
        return False

    # --- ИЗМЕНЕНИЕ: Строим путь к папке бэкапов с учетом имени расписания ---
    backup_dir = os.path.join(os.path.dirname(file_to_backup_path), 'backups', schedule_name)
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_name = os.path.basename(file_to_backup_path)
    backup_path = os.path.join(backup_dir, f"{file_name}_{timestamp}.bak")

    try:
        shutil.copy2(file_to_backup_path, backup_path)
        log.info(f"Создан бэкап '{file_name}' -> '{backup_path}'")
        return True
    except Exception as e:
        log.error(f"Не удалось создать бэкап файла '{file_to_backup_path}': {e}", exc_info=True)
        return False


def clean_old_backups(schedule_name: str, base_data_dir: str, keep_days: int = None):
    """
    Удаляет старые бэкапы из подпапки с именем расписания.
    """
    if keep_days is None:
        keep_days = Config.BACKUP_RETENTION_DAYS

    # --- ИЗМЕНЕНИЕ: Строим путь к папке бэкапов с учетом имени расписания ---
    backup_dir = os.path.join(base_data_dir, 'backups', schedule_name)

    if not os.path.exists(backup_dir):
        log.info(f"Директория бэкапов не существует: {backup_dir}. Пропуск очистки.")
        return

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    log.info(f"Начинаю очистку бэкапов в '{backup_dir}'. Удаляю файлы старше {keep_days} дней.")

    for filename in os.listdir(backup_dir):

        if not filename.endswith(".bak"):
            continue

        file_path = os.path.join(backup_dir, filename)
        if os.path.isfile(file_path):
            try:
                match = re.search(r'_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.bak$', filename)
                if match:
                    date_str = match.group(1)
                    file_date = datetime.strptime(date_str, '%Y-%m-%d_%H-%M-%S')

                    if file_date < cutoff_date:
                        os.remove(file_path)
                        log.info(f"Удален старый бэкап: {filename}")
                else:
                    log.warning(f"Не удалось найти паттерн даты в имени файла бэкапа: {filename}. Пропущен.")
            except (ValueError, IndexError, OSError) as e:
                log.warning(f"Ошибка при обработке или удалении файла бэкапа {filename}: {e}.")


# Эту функцию будет использовать schedule_comparator
def get_latest_backup_path(schedule_name: str, original_file_path: str) -> str or None:
    """
    Находит путь к самому свежему файлу бэкапа в подпапке расписания.
    """
    # --- ИЗМЕНЕНИЕ: Строим путь к папке бэкапов с учетом имени расписания ---
    backup_dir = os.path.join(os.path.dirname(original_file_path), 'backups', schedule_name)

    if not os.path.exists(backup_dir):
        return None

    latest_backup = None
    latest_timestamp = datetime.min
    file_prefix = os.path.basename(original_file_path) + "_"

    for filename in os.listdir(backup_dir):
        if filename.startswith(file_prefix) and filename.endswith(".bak"):
            match = re.search(r'_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.bak$', filename)
            if match:
                file_date = datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
                if file_date > latest_timestamp:
                    latest_timestamp = file_date
                    latest_backup = os.path.join(backup_dir, filename)

    return latest_backup