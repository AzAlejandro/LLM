"""Logging setup shared by toolkit modules.

Release 01 does not include tracing or observability infrastructure. This module
only provides a predictable ``llmkit`` logger that can write to the console and,
when requested, to a local file. Clients can use it later to record provider,
model, latency, and parsing errors without inventing their own logger setup.
"""

import logging
from pathlib import Path


def configure_logging(log_dir: Path | str | None = None) -> logging.Logger:
    """Configure and return the shared ``llmkit`` logger.

    Args:
        log_dir: Optional directory for ``llmkit.log``. When ``None``, logging is
            console-only. When a path is provided, the directory is created if it
            does not already exist.

    Returns:
        Configured ``logging.Logger`` named ``"llmkit"``.

    Notes:
        Existing handlers are cleared before adding new ones. This avoids
        duplicate log lines when notebooks re-run setup cells.
    """
    logger = logging.getLogger("llmkit")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_dir is not None:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path / "llmkit.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
