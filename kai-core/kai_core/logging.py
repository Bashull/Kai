from __future__ import annotations

import logging

from .config import SETTINGS


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, SETTINGS.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger(name)
