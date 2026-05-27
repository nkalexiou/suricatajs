# tests/test_scheduler.py
import importlib
import os
from unittest.mock import patch
from sqlalchemy import text
from db.database import get_engine


def _seed_target(url, scan_interval_minutes=None):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO targets (url, scan_interval_minutes, created_at) "
                 "VALUES (:url, :interval, '20260526_120000')"),
            {"url": url, "interval": scan_interval_minutes},
        )
        conn.commit()


def test_scheduler_uses_target_interval(fresh_db):
    _seed_target("https://a.com", scan_interval_minutes=15)
    _seed_target("https://b.com", scan_interval_minutes=None)

    added_jobs = []

    class FakeScheduler:
        def add_job(self, func, trigger, minutes, args, id):
            added_jobs.append({"minutes": minutes, "url": args[0]["url"]})
        def start(self):
            pass

    from scanner import scheduler as sched_module
    importlib.reload(sched_module)

    with patch("scanner.scheduler.BlockingScheduler", return_value=FakeScheduler()):
        with patch.dict(os.environ, {"SCAN_INTERVAL_MINUTES": "60"}):
            sched_module.start_scheduler()

    assert len(added_jobs) == 2
    a_job = next(j for j in added_jobs if j["url"] == "https://a.com")
    b_job = next(j for j in added_jobs if j["url"] == "https://b.com")
    assert a_job["minutes"] == 15
    assert b_job["minutes"] == 60


def test_scheduler_default_interval(fresh_db):
    _seed_target("https://c.com", scan_interval_minutes=None)

    added_jobs = []

    class FakeScheduler:
        def add_job(self, func, trigger, minutes, args, id):
            added_jobs.append({"minutes": minutes})
        def start(self):
            pass

    from scanner import scheduler as sched_module
    importlib.reload(sched_module)

    with patch("scanner.scheduler.BlockingScheduler", return_value=FakeScheduler()):
        with patch.dict(os.environ, {"SCAN_INTERVAL_MINUTES": "30"}):
            sched_module.start_scheduler()

    assert added_jobs[0]["minutes"] == 30


def test_scheduler_no_targets_does_not_start(fresh_db):
    started = []

    class FakeScheduler:
        def add_job(self, *args, **kwargs):
            pass
        def start(self):
            started.append(True)

    from scanner import scheduler as sched_module
    importlib.reload(sched_module)

    with patch("scanner.scheduler.BlockingScheduler", return_value=FakeScheduler()):
        with patch("scanner.loader.load_targets", return_value=[]):
            sched_module.start_scheduler()

    assert started == []
