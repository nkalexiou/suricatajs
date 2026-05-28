import logging
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("suricatajs")


def discover_urls(seed_url: str, max_depth: int) -> list:
    """BFS crawl from seed_url up to max_depth hops. Returns unique same-domain page URLs."""
    if max_depth == 0:
        return [seed_url]

    seed_domain = urlparse(seed_url).netloc
    visited = set()
    queue = deque([(seed_url, 0)])
    result = []

    while queue:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, features="lxml")
            result.append(url)

            if depth < max_depth:
                for tag in soup.find_all("a", href=True):
                    href = urljoin(url, tag["href"])
                    parsed = urlparse(href)
                    if parsed.netloc != seed_domain:
                        continue
                    clean = parsed._replace(fragment="", query="").geturl()
                    if clean not in visited:
                        queue.append((clean, depth + 1))
        except requests.RequestException as e:
            logger.warning(f"Discovery: failed to fetch {url}: {e}")

    return result
