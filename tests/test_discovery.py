from unittest.mock import patch, MagicMock
from scanner.discovery import discover_urls


def _make_html(*hrefs):
    links = "".join(f'<a href="{h}"></a>' for h in hrefs)
    return f"<html><body>{links}</body></html>"


def test_discover_depth_0_returns_only_seed():
    result = discover_urls("https://example.com/", max_depth=0)
    assert result == ["https://example.com/"]


def test_discover_same_domain_only():
    html = _make_html(
        "/about",
        "https://example.com/shop",
        "https://external.com/evil",
    )
    with patch("scanner.discovery.requests.get") as mock_get:
        mock_get.return_value = MagicMock(text=html, status_code=200)
        result = discover_urls("https://example.com/", max_depth=1)
    urls = set(result)
    assert urls == {"https://example.com/", "https://example.com/about", "https://example.com/shop"}


def test_discover_max_depth_limits_crawl():
    html_depth1 = _make_html("/page2")
    html_depth2 = _make_html("/page3")
    html_depth3 = _make_html("/page4")

    def fake_get(url, **kwargs):
        m = MagicMock(status_code=200)
        if url == "https://example.com/":
            m.text = html_depth1
        elif url == "https://example.com/page2":
            m.text = html_depth2
        elif url == "https://example.com/page3":
            m.text = html_depth3
        else:
            m.text = "<html></html>"
        return m

    with patch("scanner.discovery.requests.get", side_effect=fake_get):
        result = discover_urls("https://example.com/", max_depth=2)

    urls = set(result)
    assert urls == {"https://example.com/", "https://example.com/page2", "https://example.com/page3"}


def test_discover_no_duplicates():
    html = _make_html("/about", "/about", "/about")
    with patch("scanner.discovery.requests.get") as mock_get:
        mock_get.return_value = MagicMock(text=html, status_code=200)
        result = discover_urls("https://example.com/", max_depth=1)
    assert result.count("https://example.com/about") == 1


def test_discover_handles_request_error_on_seed():
    import requests as req
    with patch("scanner.discovery.requests.get", side_effect=req.RequestException("timeout")):
        result = discover_urls("https://example.com/", max_depth=1)
    assert result == []


def test_discover_handles_request_error_on_subpage():
    """Error on a subpage should not kill the whole crawl."""
    import requests as req
    html_seed = _make_html("/page2", "/page3")
    html_page3 = _make_html("/page4")

    call_count = {"n": 0}
    def fake_get(url, **kwargs):
        call_count["n"] += 1
        if url == "https://example.com/":
            return MagicMock(text=html_seed, status_code=200)
        if url == "https://example.com/page2":
            raise req.RequestException("timeout")
        if url == "https://example.com/page3":
            return MagicMock(text=html_page3, status_code=200)
        return MagicMock(text="<html></html>", status_code=200)

    with patch("scanner.discovery.requests.get", side_effect=fake_get):
        result = discover_urls("https://example.com/", max_depth=2)

    urls = set(result)
    assert {"https://example.com/", "https://example.com/page3"}.issubset(urls)
