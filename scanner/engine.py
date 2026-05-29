"""
Core scanning logic. Imported by run.py (standalone) and the FastAPI app (background tasks).
"""
import base64
import datetime
import difflib
import hashlib
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text as _text

from alerts_obj import Alerts
from db.database import get_connection
from webhooks.delivery import deliver_webhook
from suricatajs_obj import SuricataJSObject
from scanner.discovery import discover_urls
from scanner.playwright_scanner import get_page_scripts

logger = logging.getLogger("suricatajs")


def _compute_sri(content: str) -> str:
    digest = hashlib.sha384(content.encode("utf-8")).digest()
    return "sha384-" + base64.b64encode(digest).decode("ascii")


def _compute_diff(old_js: str, new_js: str) -> str:
    lines = difflib.unified_diff(
        old_js.splitlines(keepends=True),
        new_js.splitlines(keepends=True),
        fromfile="stored",
        tofile="current",
    )
    return "".join(lines)


def _scan_external_script(script_url: str, page_url: str):
    logger.info(f"Processing {script_url}")
    jssource = requests.get(script_url, timeout=30).text
    suricata_js = SuricataJSObject(script_url, jssource)
    is_match, stored_checksum = suricata_js.compare_with_db()
    sri = _compute_sri(jssource)

    if stored_checksum is not None:
        if not is_match:
            stored_js = suricata_js.get_stored_javascript()
            diff = _compute_diff(stored_js, jssource)
            alert = Alerts(script_url, stored_checksum, suricata_js.checksum, diff=diff, sri=sri, source_page=page_url)
            logger.warning(alert.missmatch_alert())
            alert.save_to_db()
            deliver_webhook(alert.to_dict())
            suricata_js.save_to_db()
    else:
        alert = Alerts(script_url, None, None, sri=sri, source_page=page_url)
        logger.info(alert.new_script_alert())
        alert.save_to_db()
        deliver_webhook(alert.to_dict())
        suricata_js.save_to_db()


def _scan_inline_script(page_url: str, content: str):
    content = content.strip()
    if not content:
        return
    script_id = hashlib.sha256(content.encode()).hexdigest()[:16]
    synthetic_url = f"{page_url}#inline-{script_id}"
    logger.info(f"Processing inline script {synthetic_url}")
    sri = _compute_sri(content)

    suricata_js = SuricataJSObject(synthetic_url, content)
    is_match, stored_checksum = suricata_js.compare_with_db()

    if stored_checksum is not None:
        if not is_match:
            stored_js = suricata_js.get_stored_javascript()
            diff = _compute_diff(stored_js, content)
            alert = Alerts(synthetic_url, stored_checksum, suricata_js.checksum, diff=diff, sri=sri, source_page=page_url)
            logger.warning(alert.missmatch_alert())
            alert.save_to_db()
            deliver_webhook(alert.to_dict())
            suricata_js.save_to_db()
    else:
        alert = Alerts(synthetic_url, None, None, sri=sri, source_page=page_url)
        logger.info(alert.new_script_alert())
        alert.save_to_db()
        deliver_webhook(alert.to_dict())
        suricata_js.save_to_db()


def _scan_page_with_requests(page_url: str):
    try:
        html_resp = requests.get(page_url, timeout=30).text
        soup = BeautifulSoup(html_resp, features="lxml")
        for script in soup.find_all("script"):
            src = script.get("src")
            if src:
                try:
                    script_url = urljoin(page_url, src)
                    _scan_external_script(script_url, page_url)
                except requests.RequestException as e:
                    logger.exception(f"Error fetching script {src}: {e}")
            else:
                _scan_inline_script(page_url, script.get_text())
    except requests.RequestException as e:
        logger.exception(f"Error fetching {page_url}: {e}")


def _scan_page_with_playwright(page_url: str):
    try:
        scripts = get_page_scripts(page_url)
        for script_url in scripts.get("external", []):
            try:
                _scan_external_script(script_url, page_url)
            except requests.RequestException as e:
                logger.exception(f"Error fetching script {script_url}: {e}")
        for content in scripts.get("inline", []):
            _scan_inline_script(page_url, content)
    except Exception as e:
        logger.exception(f"Error scanning {page_url} with Playwright: {e}")


def check_target(target: dict):
    """Scan a single target page URL for all its scripts."""
    targeturl = target["url"]
    crawl_depth = target.get("crawl_depth") or 0
    use_playwright = bool(target.get("use_playwright"))

    logger.info(f"Scanning {targeturl} (crawl_depth={crawl_depth}, playwright={use_playwright})")

    pages = discover_urls(targeturl, crawl_depth) if crawl_depth > 0 else [targeturl]

    for page_url in pages:
        if use_playwright:
            _scan_page_with_playwright(page_url)
        else:
            _scan_page_with_requests(page_url)

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        with get_connection() as conn:
            conn.execute(
                _text("UPDATE targets SET last_scanned_at = :ts WHERE url = :url"),
                {"ts": now, "url": targeturl},
            )
    except Exception:
        logger.exception(f"Failed to update last_scanned_at for {targeturl}")
