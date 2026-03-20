"""Application configuration for POS System."""
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    basedir = Path(sys.executable).parent
else:
    basedir = Path(__file__).resolve().parent

def _get_pos_name():
    config_path = basedir / 'pos_config.json'
    if config_path.exists():
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('POS_NAME', data.get('pos_name', 'POS System')).strip()
        except Exception:
            pass
    return (os.environ.get('POS_NAME') or 'POS System').strip()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pos-system-secret-key-change-in-production'
    POS_NAME = _get_pos_name()
    
    # Handle Render's DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # SQLAlchemy 2.0+ requires postgresql:// instead of postgres://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{basedir / "database.db"}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    
    # Security & Session
    SESSION_COOKIE_SECURE = True if os.environ.get('FLASK_ENV') == 'production' else False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    ITEMS_PER_PAGE = 20
    LOW_STOCK_THRESHOLD = 10
    BACKUP_DIR = basedir / 'backups'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
