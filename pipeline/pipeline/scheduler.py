"""Scheduler — runs the orchestrator on a configurable interval using APScheduler."""

from ..core.config import settings
from .orchestrator import ContentOrchestrator
from datetime import datetime


def run_pipeline_job():
    print(f"\n{'='*60}")
    print(f"  Pipeline Run — {datetime.now().isoformat()}")
    print(f"{'='*60}")
    orchestrator = ContentOrchestrator()
    results = orchestrator.run_all()
    print(f"  Results: {results}")
    print(f"{'='*60}\n")


def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        print("  [Scheduler] APScheduler not installed. Run: pip install apscheduler")
        print("  [Scheduler] Falling back to single run.")
        run_pipeline_job()
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_pipeline_job, "interval", hours=6, next_run_time=datetime.now())
    scheduler.start()
    print(f"  Scheduler started. Running every 6 hours.")
    print(f"  Enabled sources: {settings.SOURCES_ENABLED}")
    print(f"  Press Ctrl+C to stop.")

    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("  Scheduler stopped.")
