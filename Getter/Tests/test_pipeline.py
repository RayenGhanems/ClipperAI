from Data_Ingestion.models import Channel, Video
from Data_Ingestion.pipeline import PipelineService


class FakeSyncService:
    def __init__(self):
        self.ingest_calls = []
        self.refresh_calls = []

    def ingest_channel(self, db, channel_url, max_new_videos=None):
        self.ingest_calls.append((channel_url, max_new_videos))

        return {
            "download_video_ids": ["video-1"],
        }

    def refresh_channel(self, db, channel_url):
        self.refresh_calls.append(channel_url)

        return {
            "download_video_ids": [channel_url],
        }


class FakeDownloadService:
    def __init__(self):
        self.calls = []

    def download_videos(self, db, youtube_video_ids):
        self.calls.append(list(youtube_video_ids))

        return {
            "downloaded_count": len(youtube_video_ids),
            "failed_count": 0,
            "downloaded": [],
            "failed": [],
        }
def test_ingest_channel_uses_sync_then_download(db, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

    pipeline = PipelineService()
    pipeline.sync_service = FakeSyncService()
    pipeline.download_service = FakeDownloadService()

    result = pipeline.ingest_channel(
        db,
        "https://www.youtube.com/@channel1",
        max_new_videos=2,
    )

    assert result["download_result"]["downloaded_count"] == 1
    assert pipeline.sync_service.ingest_calls == [
        ("https://www.youtube.com/@channel1", 2),
    ]
    assert pipeline.download_service.calls == [["video-1"]]


def test_refresh_channels_uses_database_channels_when_no_urls_provided(db, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

    db.add(Channel(
        channel_id="channel-1",
        channel_name="Channel 1",
        channel_url="https://www.youtube.com/@channel1",
    ))
    db.add(Channel(
        channel_id="channel-2",
        channel_name="Channel 2",
        channel_url="https://www.youtube.com/@channel2",
    ))
    db.commit()

    pipeline = PipelineService()
    pipeline.sync_service = FakeSyncService()
    pipeline.download_service = FakeDownloadService()

    result = pipeline.refresh_channels(db)

    assert result["synced_count"] == 2
    assert pipeline.sync_service.refresh_calls == [
        "https://www.youtube.com/@channel1",
        "https://www.youtube.com/@channel2",
    ]
    assert pipeline.download_service.calls == [[
        "https://www.youtube.com/@channel1",
        "https://www.youtube.com/@channel2",
    ]]


def test_refresh_channels_uses_provided_url_list(db, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

    pipeline = PipelineService()
    pipeline.sync_service = FakeSyncService()
    pipeline.download_service = FakeDownloadService()

    result = pipeline.refresh_channels(
        db,
        ["https://www.youtube.com/@channel1"],
    )

    assert result["synced_count"] == 1
    assert pipeline.sync_service.refresh_calls == [
        "https://www.youtube.com/@channel1",
    ]
