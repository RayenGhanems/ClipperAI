import logging
import os
import time

from Data_Ingestion.database import SessionLocal
from Data_Ingestion.pipeline import PipelineService


DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
CHANNEL_URLS_ENV_VAR = "SYNC_CHANNEL_URLS"

logger = logging.getLogger(__name__)


def get_interval_seconds() -> int:
    # Par défaut, relancer le scheduler toutes les 24 heures.
    raw_value = os.getenv("SYNC_INTERVAL_SECONDS")

    if raw_value is None or raw_value == "":
        return DEFAULT_INTERVAL_SECONDS

    interval = int(raw_value)

    if interval <= 0:
        raise ValueError("SYNC_INTERVAL_SECONDS must be greater than 0")

    return interval


def get_channel_urls_from_environment() -> list[str] | None:
    # Permettre une liste d'URLs séparées par des virgules pour cibler certaines chaînes.
    raw_value = os.getenv(CHANNEL_URLS_ENV_VAR)

    if raw_value is None or raw_value.strip() == "":
        return None

    channel_urls = [
        url.strip()
        for url in raw_value.split(",")
        if url.strip()
    ]

    return channel_urls or None


def run_once(channel_urls: list[str] | None = None):
    # Exécuter un cycle complet: ouvrir la session, lancer le pipeline, puis fermer la session.
    db = SessionLocal()

    try:
        pipeline = PipelineService()
        resolved_channel_urls = (
            channel_urls if channel_urls is not None
            else get_channel_urls_from_environment()
        )

        result = pipeline.refresh_channels(db, resolved_channel_urls)

        logger.info(
            "Scheduler run finished: synced=%s failed=%s downloaded=%s",
            result["synced_count"],
            result["failed_count"],
            result["download_result"]["downloaded_count"],
        )

        return result

    finally:
        db.close()


def run_forever(
    interval_seconds: int | None = None,
    channel_urls: list[str] | None = None,
):
    # Refaire le même cycle à intervalle régulier.
    if interval_seconds is None:
        interval_seconds = get_interval_seconds()

    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    logger.info("Scheduler started with interval=%s seconds", interval_seconds)

    while True:
        try:
            run_once(channel_urls=channel_urls)
        except Exception:
            logger.exception("Scheduler run failed")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    run_forever()
