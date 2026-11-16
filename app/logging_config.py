"""Единая настройка логирования TaskFlow через переменную LOG_LEVEL."""

import logging
import sys

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(level: str) -> None:
    """Настроить консольные логи; неизвестный уровень считать ошибкой конфигурации."""
    level_name = level.strip().upper()
    numeric_level = LOG_LEVELS.get(level_name)
    if numeric_level is None:
        supported_levels = ", ".join(LOG_LEVELS)
        raise ValueError(
            f"Unsupported LOG_LEVEL {level!r}. Choose one of: {supported_levels}."
        )

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger().setLevel(numeric_level)
