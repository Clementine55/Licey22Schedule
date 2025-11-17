# wsgi.py
from app import create_app

# Gunicorn будет искать именно эту переменную `app`
app = create_app()