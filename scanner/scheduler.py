import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger("suricatajs")


def start_scheduler(targets_file: str = "targets.txt") -> None:
    from run import check_target
    from scanner.loader import load_targets

    scheduler = BlockingScheduler()
    global_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))
    targets = load_targets(targets_file)

    if not targets:
        logger.warning("No targets found; scheduler has nothing to schedule.")
        return

    for target in targets:
        interval = target.get("scan_interval_minutes") or global_interval
        try:
            scheduler.add_job(
                check_target,
                "interval",
                minutes=interval,
                args=[target],
                id=f"scan_{target['url']}",
            )
            logger.info(f"Scheduled {target['url']} every {interval} minutes")
        except Exception:
            logger.exception(f"Failed to schedule {target['url']}; skipping")

    try:
        logger.info(f"Scheduler starting with {len(targets)} target(s).")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
    except Exception:
        logger.exception("Scheduler encountered an unexpected error.")
        raise
