"""Structured logging configuration for AquaSynex Backend.

Ensures logs are clean, helpful, and free of secrets or raw dumps of big datasets.
"""

import logging
import sys
from backend.config import settings


def setup_logger(name: str = "aquasynex") -> logging.Logger:
    """Configure and return application logger."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        level_name = settings.LOG_LEVEL.upper()
        level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
