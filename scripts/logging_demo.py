"""Печатает по одному сообщению каждого уровня логирования TaskFlow.

Запуск из корня проекта:
    Linux/macOS: LOG_LEVEL=DEBUG python scripts/logging_demo.py
    PowerShell:  $env:LOG_LEVEL = "DEBUG"; python scripts/logging_demo.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.logging_config import configure_logging  # noqa: E402


def main() -> None:
    configure_logging(settings.log_level)
    logger = logging.getLogger("taskflow.logging_demo")

    logger.debug("Example DEBUG message: diagnostic details")
    logger.info("Example INFO message: normal application event")
    logger.warning("Example WARNING message: recoverable issue")
    logger.error("Example ERROR message: operation failed")
    logger.critical("Example CRITICAL message: service requires immediate attention")


if __name__ == "__main__":
    main()
