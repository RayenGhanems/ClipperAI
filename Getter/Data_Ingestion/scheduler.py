import logging
import os
import time

from Data_Ingestion.database import SessionLocal
from Data_Ingestion.pipeline import PipelineService


DEFAULT_INTERVAL_SECONDS = 30 * 60

logger = logging.getLogger(__name__)


def get_interval_seconds() -> int:
    raw_value = os.getenv("SYNC_INTERVAL_SECONDS")

    if raw_value is None:
        return DEFAULT_INTERVAL_SECONDS

    interval = int(raw_value)

    if interval <= 0:
        raise ValueError("SYNC_INTERVAL_SECONDS must be greater than 0")

    return interval


def run_once():
    db = SessionLocal()

    try:
        pipeline = PipelineService()
        result = pipeline.sync_and_download_existing_channels(db)

        logger.info(
            "Scheduler run finished: synced=%s failed=%s downloaded=%s",
            result["sync_result"]["synced_count"],
            result["sync_result"]["failed_count"],
            result["download_result"]["downloaded_count"],
        )

        return result

    finally:
        db.close()


def run_forever(interval_seconds: int | None = None):
    if interval_seconds is None:
        interval_seconds = get_interval_seconds()

    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    logger.info("Scheduler started with interval=%s seconds", interval_seconds)

    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Scheduler run failed")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    run_forever()
