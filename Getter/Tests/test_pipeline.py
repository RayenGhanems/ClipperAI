from Data_Ingestion.models import Channel, Video
from Data_Ingestion.pipeline import PipelineService


class FakeSyncService:

    def __init__(self):
        self.synced_urls = []

    def sync_channel(self, db, channel_url):
        self.synced_urls.append(channel_url)

        return {
            "channel_name": "Test Channel",
            "new_videos_found": 0,
        }


class FakeDownloadService:

    def __init__(self):
        self.called = False

    def download_pending_videos(self, db):
        self.called = True

        return {
            "downloaded_count": 0,
            "failed_count": 0,
            "downloaded": [],
            "failed": [],
        }


def test_sync_existing_channels_uses_channels_already_in_database(db):
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

    result = pipeline.sync_existing_channels(db)

    assert result["total_channels"] == 2
    assert result["synced_count"] == 2
    assert result["failed_count"] == 0
    assert pipeline.sync_service.synced_urls == [
        "https://www.youtube.com/@channel1",
        "https://www.youtube.com/@channel2",
    ]


def test_sync_and_download_existing_channels_downloads_pending_videos(db):
    db.add(Channel(
        id=1,
        channel_id="channel-1",
        channel_name="Channel 1",
        channel_url="https://www.youtube.com/@channel1",
    ))
    db.add(Video(
        channel_db_id=1,
        youtube_video_id="video-1",
        title="Video 1",
        youtube_url="https://www.youtube.com/watch?v=video-1",
        download_status="PENDING",
    ))
    db.commit()

    pipeline = PipelineService()
    pipeline.sync_service = FakeSyncService()
    pipeline.download_service = FakeDownloadService()

    result = pipeline.sync_and_download_existing_channels(db)

    assert result["sync_result"]["synced_count"] == 1
    assert result["pending_videos_before_download"] == 1
    assert result["download_result"]["downloaded_count"] == 0
    assert pipeline.download_service.called is True
