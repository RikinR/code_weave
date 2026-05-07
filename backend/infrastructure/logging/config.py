from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = _BACKEND_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "encoding": "utf-8",
            "formatter": "detailed",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "application": {"level": "DEBUG", "propagate": True},
        "infrastructure": {"level": "DEBUG", "propagate": True},
        "app": {"level": "DEBUG", "propagate": True},
        "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
}