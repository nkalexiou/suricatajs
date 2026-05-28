import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger("suricatajs")


def get_page_scripts(url: str) -> dict:
    """
    Load url in headless Chromium and extract all script src URLs and inline script content.
    Returns {"external": [url, ...], "inline": [content, ...]}.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)

            external = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('script[src]'))
                    .map(s => s.src)
                    .filter(s => s.length > 0);
            }""")

            inline = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('script:not([src])'))
                    .map(s => s.textContent || '');
            }""")
        finally:
            browser.close()

    return {
        "external": external or [],
        "inline": [c for c in (inline or []) if c.strip()],
    }
