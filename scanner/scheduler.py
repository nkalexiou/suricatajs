import logging
import os

logger = logging.getLogger("suricatajs")

# Defined at module level so tests can patch "scanner.scheduler.BlockingScheduler".
# The real class is imported lazily on first call to start_scheduler().
BlockingScheduler = None


def start_scheduler(targets_file: str = "targets.txt") -> None:
    global BlockingScheduler
    from run import check_target
    from scanner.loader import load_targets

    if BlockingScheduler is None:
        from apscheduler.schedulers.blocking import BlockingScheduler as _BS
        BlockingScheduler = _BS

    scheduler = BlockingScheduler()
    global_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))
    targets = load_targets(targets_file)

    if not targets:
        logger.warning("No targets found; scheduler has nothing to schedule.")
        return

    for target in targets:
        interval = target.get("scan_interval_minutes") or global_interval
        logger.info(f"Scheduling {target['url']} every {interval} minutes")
        scheduler.add_job(
            check_target,
            "interval",
            minutes=interval,
            args=[target],
            id=f"scan_{target['url']}",
        )

    logger.info(f"Scheduler starting with {len(targets)} target(s).")
    scheduler.start()
