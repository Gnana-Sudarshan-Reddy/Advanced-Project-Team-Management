"""Application logging configuration."""
import logging
import logging.handlers
import os

from app.core.config import settings


def setup_logging() -> None:
    """Configure rotating file logging (or console-only when LOG_FILE is empty)."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return  # already configured

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    if settings.LOG_FILE:
        os.makedirs(os.path.dirname(settings.LOG_FILE) or ".", exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE, maxBytes=5_000_000, backupCount=3
        )
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    root.addHandler(handler)