from unittest.mock import patch, MagicMock
from scanner.playwright_scanner import get_page_scripts


def _make_mock_pw(external_scripts, inline_scripts):
    """Build a fully mocked playwright context manager chain."""
    mock_page = MagicMock()
    mock_page.evaluate.side_effect = [external_scripts, inline_scripts]
    mock_page.goto.return_value = None

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    # Make sync_playwright() return a context manager that yields mock_pw
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_pw)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm, mock_browser


def test_get_page_scripts_returns_external_and_inline():
    mock_cm, mock_browser = _make_mock_pw(
        ["https://cdn.example.com/a.js", "https://cdn.example.com/b.js"],
        ["console.log('hello');", ""],
    )
    with patch("scanner.playwright_scanner.sync_playwright", return_value=mock_cm):
        result = get_page_scripts("https://example.com/")

    assert "external" in result
    assert "inline" in result
    assert "https://cdn.example.com/a.js" in result["external"]
    assert "https://cdn.example.com/b.js" in result["external"]
    mock_browser.close.assert_called_once()


def test_get_page_scripts_filters_empty_inline():
    mock_cm, _ = _make_mock_pw([], ["", "   ", "valid code();"])
    with patch("scanner.playwright_scanner.sync_playwright", return_value=mock_cm):
        result = get_page_scripts("https://example.com/")

    assert result["inline"] == ["valid code();"]


def test_get_page_scripts_closes_browser_on_exception():
    mock_page = MagicMock()
    mock_page.goto.side_effect = Exception("navigation failed")
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_pw)
    mock_cm.__exit__ = MagicMock(return_value=False)

    with patch("scanner.playwright_scanner.sync_playwright", return_value=mock_cm):
        try:
            get_page_scripts("https://example.com/")
        except Exception:
            pass

    mock_browser.close.assert_called_once()
