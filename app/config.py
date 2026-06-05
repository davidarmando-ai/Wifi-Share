import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'wifishare-dev-secret-2025')
    DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'wifishare.db')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
