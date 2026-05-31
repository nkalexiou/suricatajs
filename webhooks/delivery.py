import logging
import os
import time
from urllib.parse import urlparse

import requests

logger = logging.getLogger("suricatajs")

_MAX_ATTEMPTS = 3


def deliver_webhook(payload: dict) -> None:
    """POST payload to WEBHOOK_URL. Retries up to 3 times with exponential backoff. No-ops if WEBHOOK_URL is unset."""
    url = os.getenv("WEBHOOK_URL", "").strip()
    if not url:
        return
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        logger.error("WEBHOOK_URL is not a valid http/https URL — skipping delivery")
        return

    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"Webhook delivered to {url} (attempt {attempt + 1})")
            return
        except requests.RequestException as e:
            logger.warning(f"Webhook delivery attempt {attempt + 1} failed: {e}")
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2 ** attempt)

    logger.error(f"Webhook delivery failed after {_MAX_ATTEMPTS} attempts to {url}")
