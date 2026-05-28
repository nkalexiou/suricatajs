import pytest
from unittest.mock import patch, MagicMock, call


SIMPLE_HTML = """
<html><body>
  <script src="https://cdn.example.com/a.js"></script>
  <script>console.log('inline');</script>
</body></html>
"""


def _mock_requests_html():
    m = MagicMock()
    m.text = SIMPLE_HTML
    return m


def _mock_requests_js():
    m = MagicMock()
    m.text = "var x=1;"
    return m


def test_check_target_default_uses_requests(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()

    target = {"url": "https://example.com/", "crawl_depth": 0, "use_playwright": False}

    with patch("run.requests.get", return_value=_mock_requests_html()):
        with patch("run._scan_external_script") as mock_ext:
            with patch("run._scan_inline_script") as mock_inl:
                from run import check_target
                check_target(target)

    mock_ext.assert_called_once_with("https://cdn.example.com/a.js")
    mock_inl.assert_called_once()
    reset_engine()


def test_check_target_with_crawl_depth_discovers_subpages(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()

    target = {"url": "https://example.com/", "crawl_depth": 1, "use_playwright": False}
    discovered = ["https://example.com/", "https://example.com/shop"]

    with patch("run.discover_urls", return_value=discovered) as mock_disc:
        with patch("run.requests.get", return_value=_mock_requests_html()):
            with patch("run._scan_external_script"):
                with patch("run._scan_inline_script"):
                    from run import check_target
                    check_target(target)

    mock_disc.assert_called_once_with("https://example.com/", 1)
    reset_engine()


def test_check_target_with_playwright_uses_playwright_scanner(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()

    target = {"url": "https://example.com/", "crawl_depth": 0, "use_playwright": True}
    pw_result = {
        "external": ["https://cdn.example.com/a.js"],
        "inline": ["console.log('test');"],
    }

    with patch("run.get_page_scripts", return_value=pw_result) as mock_pw:
        with patch("run._scan_external_script") as mock_ext:
            with patch("run._scan_inline_script") as mock_inl:
                from run import check_target
                check_target(target)

    mock_pw.assert_called_once_with("https://example.com/")
    mock_ext.assert_called_once_with("https://cdn.example.com/a.js")
    mock_inl.assert_called_once_with("https://example.com/", "console.log('test');")
    reset_engine()


def test_check_target_missing_keys_use_defaults(tmp_path, monkeypatch):
    """check_target must handle target dicts that lack crawl_depth/use_playwright (e.g. from YAML file)."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()

    target = {"url": "https://example.com/"}

    with patch("run.requests.get", return_value=_mock_requests_html()):
        with patch("run._scan_external_script"):
            with patch("run._scan_inline_script"):
                from run import check_target
                check_target(target)  # must not raise KeyError
    reset_engine()
