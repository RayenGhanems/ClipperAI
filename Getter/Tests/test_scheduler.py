import pytest

from Data_Ingestion import scheduler


class FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakePipelineService:
    last_db = None
    last_channel_urls = None

    def refresh_channels(self, db, channel_urls=None):
        self.__class__.last_db = db
        self.__class__.last_channel_urls = channel_urls

        return {
            "synced_count": 2,
            "failed_count": 0,
            "download_result": {
                "downloaded_count": 1,
            },
        }


def test_scheduler_run_once_uses_database_session_and_closes_it(monkeypatch):
    fake_session = FakeSession()

    monkeypatch.setattr(scheduler, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(scheduler, "PipelineService", FakePipelineService)

    result = scheduler.run_once(["https://www.youtube.com/@channel1"])

    assert result["synced_count"] == 2
    assert result["download_result"]["downloaded_count"] == 1
    assert FakePipelineService.last_db is fake_session
    assert FakePipelineService.last_channel_urls == [
        "https://www.youtube.com/@channel1"
    ]
    assert fake_session.closed is True


def test_scheduler_interval_comes_from_environment(monkeypatch):
    monkeypatch.setenv("SYNC_INTERVAL_SECONDS", "60")

    assert scheduler.get_interval_seconds() == 60


def test_scheduler_uses_24h_default_interval(monkeypatch):
    monkeypatch.delenv("SYNC_INTERVAL_SECONDS", raising=False)

    assert scheduler.get_interval_seconds() == 24 * 60 * 60


def test_scheduler_rejects_invalid_interval(monkeypatch):
    monkeypatch.setenv("SYNC_INTERVAL_SECONDS", "0")

    with pytest.raises(ValueError):
        scheduler.get_interval_seconds()


def test_scheduler_channel_urls_come_from_environment(monkeypatch):
    monkeypatch.setenv(
        "SYNC_CHANNEL_URLS",
        "https://www.youtube.com/@channel1, https://www.youtube.com/@channel2",
    )

    assert scheduler.get_channel_urls_from_environment() == [
        "https://www.youtube.com/@channel1",
        "https://www.youtube.com/@channel2",
    ]
