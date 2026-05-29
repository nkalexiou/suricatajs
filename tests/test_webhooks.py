import os
import pytest
from unittest.mock import patch, MagicMock, call


def test_deliver_webhook_skips_when_no_url(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    from webhooks.delivery import deliver_webhook
    with patch("webhooks.delivery.requests.post") as mock_post:
        deliver_webhook({"alert_type": "new_script"})
    mock_post.assert_not_called()


def test_deliver_webhook_posts_payload(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.com/notify")
    from webhooks.delivery import deliver_webhook

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None

    with patch("webhooks.delivery.requests.post", return_value=mock_resp) as mock_post:
        deliver_webhook({"alert_type": "checksum", "javascript": "https://a.com/a.js"})

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["alert_type"] == "checksum"
    assert kwargs["json"]["javascript"] == "https://a.com/a.js"
    assert kwargs["timeout"] == 10


def test_deliver_webhook_retries_on_500(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.com/notify")
    from webhooks.delivery import deliver_webhook
    import requests as req

    fail_resp = MagicMock()
    fail_resp.status_code = 500
    fail_resp.raise_for_status.side_effect = req.HTTPError("500")

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.raise_for_status.return_value = None

    with patch("webhooks.delivery.requests.post", side_effect=[fail_resp, ok_resp]) as mock_post:
        with patch("webhooks.delivery.time.sleep"):
            deliver_webhook({"alert_type": "new_script"})

    assert mock_post.call_count == 2


def test_deliver_webhook_retries_on_connection_error(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.com/notify")
    from webhooks.delivery import deliver_webhook
    import requests as req

    with patch("webhooks.delivery.requests.post",
               side_effect=req.ConnectionError("refused")) as mock_post:
        with patch("webhooks.delivery.time.sleep"):
            deliver_webhook({"alert_type": "new_script"})

    assert mock_post.call_count == 3


def test_deliver_webhook_exponential_backoff(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.com/notify")
    from webhooks.delivery import deliver_webhook
    import requests as req

    with patch("webhooks.delivery.requests.post",
               side_effect=req.ConnectionError("refused")):
        with patch("webhooks.delivery.time.sleep") as mock_sleep:
            deliver_webhook({"alert_type": "new_script"})

    delays = [c.args[0] for c in mock_sleep.call_args_list]
    assert delays == [1, 2]


def test_run_delivers_webhook_on_new_script(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.com/notify")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()

    mock_resp = MagicMock()
    mock_resp.text = "var x=1;"
    http_ok = MagicMock(status_code=200)
    http_ok.raise_for_status.return_value = None

    with patch("run.requests.get", return_value=mock_resp):
        with patch("webhooks.delivery.requests.post", return_value=http_ok) as mock_post:
            from run import _scan_external_script
            _scan_external_script("https://a.com/a.js")

    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["alert_type"] == "new_script"
    assert payload["javascript"] == "https://a.com/a.js"
    reset_engine()
