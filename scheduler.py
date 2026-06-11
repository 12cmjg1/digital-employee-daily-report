from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from main import run_daily_report, run_weekly_report


TIMEZONE = "Asia/Shanghai"
DEFAULT_CONFIG = "config.real.yaml"
LOG_PATH = Path("logs/scheduler.log")


def _log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    LOG_PATH.write_text(
        (LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else "")
        + f"[{now}] {message}\n",
        encoding="utf-8",
    )


def daily_job(config_path: str = DEFAULT_CONFIG) -> None:
    _log(f"daily job started: {config_path}")
    run_daily_report(config_path, include_weekly=False)
    _log("daily job finished")


def weekly_job(config_path: str = DEFAULT_CONFIG) -> None:
    _log(f"weekly job started: {config_path}")
    report_date = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    run_daily_report(config_path, include_weekly=False)
    run_weekly_report(report_date)
    _log("weekly job finished")


def run_daemon(config_path: str = DEFAULT_CONFIG) -> None:
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(daily_job, "cron", hour=8, minute=0, args=[config_path], id="daily_report")
    scheduler.add_job(
        weekly_job,
        "cron",
        day_of_week="sun",
        hour=8,
        minute=20,
        args=[config_path],
        id="weekly_report",
    )
    _log("scheduler daemon started")
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scheduled report runner.")
    parser.add_argument("job", choices=["daily", "weekly", "daemon"])
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    if args.job == "daily":
        daily_job(args.config)
    elif args.job == "weekly":
        weekly_job(args.config)
    else:
        run_daemon(args.config)


if __name__ == "__main__":
    main()
