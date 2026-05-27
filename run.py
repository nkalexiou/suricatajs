"""
Main suricatajs file. Scanner logic lives in check() and check_target().
"""
import difflib
import hashlib
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from alerts_obj import Alerts
from db.database import init_db
from suricatajs_obj import SuricataJSObject

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


def _compute_diff(old_js: str, new_js: str) -> str:
    lines = difflib.unified_diff(
        old_js.splitlines(keepends=True),
        new_js.splitlines(keepends=True),
        fromfile="stored",
        tofile="current",
    )
    return "".join(lines)


def _scan_external_script(script_url: str):
    logger.info(f"Processing {script_url}")
    jssource = requests.get(script_url, timeout=30).text
    suricata_js = SuricataJSObject(script_url, jssource)
    is_match, stored_checksum = suricata_js.compare_with_db()

    if stored_checksum is not None:
        if not is_match:
            stored_js = suricata_js.get_stored_javascript()
            diff = _compute_diff(stored_js, jssource)
            alert = Alerts(script_url, stored_checksum, suricata_js.checksum, diff=diff)
            logger.warning(alert.missmatch_alert())
            alert.save_to_db()
            suricata_js.save_to_db()
    else:
        alert = Alerts(script_url, None, None)
        logger.info(alert.new_script_alert())
        alert.save_to_db()
        suricata_js.save_to_db()


def _scan_inline_script(page_url: str, content: str):
    content = content.strip()
    if not content:
        return
    script_id = hashlib.sha256(content.encode()).hexdigest()[:16]
    synthetic_url = f"{page_url}#inline-{script_id}"
    logger.info(f"Processing inline script {synthetic_url}")

    suricata_js = SuricataJSObject(synthetic_url, content)
    is_match, stored_checksum = suricata_js.compare_with_db()

    if stored_checksum is not None:
        if not is_match:
            stored_js = suricata_js.get_stored_javascript()
            diff = _compute_diff(stored_js, content)
            alert = Alerts(synthetic_url, stored_checksum, suricata_js.checksum, diff=diff)
            logger.warning(alert.missmatch_alert())
            alert.save_to_db()
            suricata_js.save_to_db()
    else:
        alert = Alerts(synthetic_url, None, None)
        logger.info(alert.new_script_alert())
        alert.save_to_db()
        suricata_js.save_to_db()


def check_target(target: dict):
    """Scan a single target page URL for all its scripts."""
    targeturl = target["url"]
    logger.info(f"Scanning {targeturl}")
    try:
        html_resp = requests.get(targeturl, timeout=30).text
        soup = BeautifulSoup(html_resp, features="lxml")

        for script in soup.find_all("script"):
            src = script.get("src")
            if src:
                try:
                    script_url = urljoin(targeturl, src)
                    _scan_external_script(script_url)
                except requests.RequestException as e:
                    logger.exception(f"Error fetching script {src}: {e}")
            else:
                _scan_inline_script(targeturl, script.get_text())

    except requests.RequestException as e:
        logger.exception(f"Error fetching {targeturl}: {e}")


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
