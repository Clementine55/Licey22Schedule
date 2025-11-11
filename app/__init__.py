import os
from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
# --- ШАГ 3.1: ИМПОРТИРУЕМ BASE_DIR ---
from config import BASE_DIR


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    if not app.debug:
        # --- ШАГ 3.2: ИЗМЕНЕНИЕ: ИСПОЛЬЗУЕМ АБСОЛЮТНЫЕ ПУТИ ДЛЯ ЛОГОВ ---
        data_dir = os.path.join(BASE_DIR, 'data')
        logs_dir = os.path.join(BASE_DIR, 'logs')
        log_file = os.path.join(logs_dir, 'app.log')

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Приложение School Schedule запущено')

    from . import routes
    app.register_blueprint(routes.bp)

    from . import api_routes
    app.register_blueprint(api_routes.bp)

    return app