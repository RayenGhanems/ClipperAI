from datetime import datetime

from Data_Ingestion.Synchronisation import SyncService
from Data_Ingestion.models import Channel, Video


class FakeYoutubeService:
    def get_channel_info(self, channel_url):
        return {
            "channel_id": "channel-1",
            "channel_name": "Channel 1",
            "channel_url": channel_url,
            "youtube_video_count": 3,
            "uploads_playlist_id": "playlist-1",
        }

    def get_channel_videos(self, uploads_playlist_id, max_pages=5, max_videos=None):
        videos = [
            {
                "youtube_video_id": "video-3",
                "title": "Video 3",
                "published_at": "2024-01-03T12:00:00Z",
                "youtube_url": "https://www.youtube.com/watch?v=video-3",
                "duration_seconds": 24,
            },
            {
                "youtube_video_id": "video-2",
                "title": "Video 2",
                "published_at": "2024-01-02T12:00:00Z",
                "youtube_url": "https://www.youtube.com/watch?v=video-2",
                "duration_seconds": 240,
            },
            {
                "youtube_video_id": "video-1",
                "title": "Video 1",
                "published_at": "2024-01-01T12:00:00Z",
                "youtube_url": "https://www.youtube.com/watch?v=video-1",
                "duration_seconds": 300,
            },
        ]

        if max_videos is not None:
            return videos[:max_videos]

        return videos


def test_sync_service_instantiation():
    service = SyncService()

    assert service is not None


def test_ingest_channel_with_limit_adds_only_requested_videos(db):
    service = SyncService()
    service.youtube_service = FakeYoutubeService()

    result = service.ingest_channel(
        db,
        "https://www.youtube.com/@channel1",
        max_new_videos=2,
    )

    channel = db.query(Channel).one()
    videos = db.query(Video).filter(Video.channel_db_id == channel.id).all()

    assert result["new_videos_found"] == 2
    assert result["download_video_ids"] == ["video-2", "video-1"]
    assert result["latest_download"] == datetime(2024, 1, 2, 12, 0, 0)
    assert len(videos) == 2


def test_ingest_channel_with_zero_updates_latest_download_without_inserting_videos(db):
    service = SyncService()
    service.youtube_service = FakeYoutubeService()

    result = service.ingest_channel(
        db,
        "https://www.youtube.com/@channel1",
        max_new_videos=0,
    )

    videos = db.query(Video).all()
    channel = db.query(Channel).one()

    assert result["new_videos_found"] == 0
    assert result["download_video_ids"] == []
    assert result["latest_download"] == datetime(2024, 1, 2, 12, 0, 0)
    assert len(videos) == 0
    assert channel.latest_download == datetime(2024, 1, 2, 12, 0, 0)


def test_refresh_channel_adds_new_latest_video_only_when_channel_already_tracked(db):
    db.add(Channel(
        id=1,
        channel_id="channel-1",
        channel_name="Channel 1",
        channel_url="https://www.youtube.com/@channel1",
        uploads_playlist_id="playlist-1",
        latest_download=datetime(2024, 1, 1, 12, 0, 0),
    ))
    db.commit()

    service = SyncService()
    service.youtube_service = FakeYoutubeService()

    result = service.refresh_channel(db, "https://www.youtube.com/@channel1")

    videos = db.query(Video).filter(Video.channel_db_id == 1).all()
    channel = db.query(Channel).one()

    assert result["download_video_ids"] == ["video-2"]
    assert result["new_videos_found"] == 1
    assert len(videos) == 1
    assert channel.latest_download == datetime(2024, 1, 2, 12, 0, 0)


def test_refresh_channel_creates_channel_without_downloading_when_missing(db):
    service = SyncService()
    service.youtube_service = FakeYoutubeService()

    result = service.refresh_channel(db, "https://www.youtube.com/@channel1")

    channel = db.query(Channel).one()
    videos = db.query(Video).all()

    assert result["channel_created"] is True
    assert result["download_video_ids"] == []
    assert channel.latest_download == datetime(2024, 1, 2, 12, 0, 0)
    assert len(videos) == 0
