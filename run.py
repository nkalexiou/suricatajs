"""
Main suricatajs file. Scanner logic lives in scanner/engine.py.
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from db.database import init_db
from scanner.engine import check_target  # noqa: F401 — re-exported for scheduler

logger = logging.getLogger("suricatajs")


def configure_logger(log_file):
    logger.setLevel(logging.DEBUG)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def check(targets_file: str = "targets.txt"):
    """Scan all targets. Loads from DB first; falls back to targets file."""
    from scanner.loader import load_targets
    targets = load_targets(targets_file)
    for target in targets:
        check_target(target)


if __name__ == "__main__":
    init_db()
    configure_logger(os.path.expanduser("./log/app.log"))
    scan_mode = os.getenv("SCAN_MODE", "once")
    if scan_mode == "scheduled":
        from scanner.scheduler import start_scheduler
        start_scheduler()
    else:
        check()
