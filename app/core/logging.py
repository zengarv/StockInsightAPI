"""
Logging configuration for the Kalpi Tech API.
"""
import logging
import logging.config
import sys
from typing import Any, Dict
from app.core.config import settings


def setup_logging() -> None:
    """Set up logging configuration."""
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": "DEBUG" if settings.DEBUG else "INFO",
                "propagate": True,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)


# Get logger instance
logger = logging.getLogger(__name__)
