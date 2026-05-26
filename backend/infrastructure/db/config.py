"""Environment-driven PostgreSQL connection settings.

Loads ``backend/.env`` and exposes ``DATABASE_URL`` for
:mod:`infrastructure.db.session` and bootstrap helpers. Missing required keys
are logged at startup so misconfiguration surfaces early.
"""

import os
from dotenv import load_dotenv
from infrastructure.logging.logger import get_logger
load_dotenv()
logger = get_logger(__name__)
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
_REQUIRED_DB_KEYS = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
_missing = [k for k in _REQUIRED_DB_KEYS if not os.getenv(k)]
if _missing:
    logger.warning('database env incomplete — missing: %s (ORM URL may be invalid until set)', ', '.join(_missing))
else:
    logger.info('database configuration: env vars present for connection')
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
