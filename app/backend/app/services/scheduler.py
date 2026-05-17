"""APScheduler — 每日續約偵測排程"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.renewals import compute_renewal_status

logger = logging.getLogger("tmca.scheduler")

_scheduler: AsyncIOScheduler | None = None


def _run_compute_renewal():
    """Scheduler job wrapper — 自己開 session、catch 例外、寫 log。"""
    db = SessionLocal()
    try:
        result = compute_renewal_status(db)
        logger.info("[renewal] computed: %s", result)
    except Exception:
        logger.exception("[renewal] compute failed")
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = AsyncIOScheduler(timezone=settings.timezone)
    # 每日 06:00 (Asia/Taipei)
    sched.add_job(
        _run_compute_renewal,
        CronTrigger(hour=6, minute=0),
        id="daily_renewal_compute",
        name="每日 06:00 續約偵測",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    sched.start()
    _scheduler = sched
    logger.info("[scheduler] started; jobs: %s", [j.id for j in sched.get_jobs()])
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
