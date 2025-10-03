# app/__init__.py

import os
from flask import Flask
import logging
from logging.handlers import RotatingFileHandler


# config.py не импортируется здесь, так как он больше не нужен для создания папок

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # --- НАСТРОЙКА ЛОГГИРОВАНИЯ ---
    if not app.debug:
        # Указываем папку для хранения данных напрямую
        data_dir = 'data'

        # Создаем папку для данных, если ее нет
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Создаем папку для логов, если ее нет
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # Настройка логгера для записи в файл
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Приложение School Schedule запущено')

    # --- РЕГИСТРАЦИЯ BLUEPRINT ---
    from . import routes
    app.register_blueprint(routes.bp)

    from . import api_routes
    app.register_blueprint(api_routes.bp)

    return app