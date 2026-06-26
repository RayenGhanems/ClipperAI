import os

from Data_Ingestion.download import DownloadService
from Data_Ingestion.models import Channel, Video


class FakeDownloadService(DownloadService):

    def download_video(self, video):
        video_path = os.path.join(
            self.output_dir,
            f"{video.youtube_video_id}.mp4"
        )

        with open(video_path, "wb") as file:
            file.write(b"fake video")

        return video_path

    def extract_audio(self, video_path):
        wav_dir = os.path.join(self.storage_root, "wav")
        os.makedirs(wav_dir, exist_ok=True)

        video_id = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(wav_dir, f"{video_id}.wav")

        with open(audio_path, "wb") as file:
            file.write(b"fake audio")

        return audio_path


class NoDownloadService(FakeDownloadService):

    def download_video(self, video):
        raise AssertionError("download_video should not be called")

    def extract_audio(self, video_path):
        raise AssertionError("extract_audio should not be called")


def test_raw_video_directory_created(tmp_path):

    output_dir = tmp_path / "raw_videos"

    DownloadService(output_dir=str(output_dir))

    assert os.path.exists(output_dir)


def test_wav_directory_creation(tmp_path):

    wav_dir = tmp_path / "wav"

    os.makedirs(wav_dir, exist_ok=True)

    assert os.path.exists(wav_dir)


def test_download_service_stores_paths_relative_to_storage_root(tmp_path):

    service = DownloadService(storage_root=str(tmp_path))

    video_path = tmp_path / "raw_videos" / "video-1.mp4"
    audio_path = tmp_path / "wav" / "video-1.wav"

    assert service.to_relative_path(str(video_path)) == "raw_videos/video-1.mp4"
    assert service.to_relative_path(str(audio_path)) == "wav/video-1.wav"


def test_download_videos_uses_shared_storage_relative_paths(db, tmp_path):

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

    service = FakeDownloadService(storage_root=str(tmp_path))

    result = service.download_videos(db, ["video-1"])
    video = db.query(Video).filter(Video.youtube_video_id == "video-1").one()

    assert result["downloaded_count"] == 1
    assert result["failed_count"] == 0
    assert video.download_status == "DOWNLOADED"
    assert video.processing_status == "WAITING_CLIPS"
    assert video.local_path == "raw_videos/video-1.mp4"
    assert video.local_audio_path == "wav/video-1.wav"
    assert os.path.exists(tmp_path / video.local_path)
    assert os.path.exists(tmp_path / video.local_audio_path)


def test_download_videos_reuses_files_already_in_shared_storage(db, tmp_path):

    raw_videos_dir = tmp_path / "raw_videos"
    wav_dir = tmp_path / "wav"
    raw_videos_dir.mkdir()
    wav_dir.mkdir()

    video_file = raw_videos_dir / "video-1.mp4"
    audio_file = wav_dir / "video-1.wav"
    video_file.write_bytes(b"existing video")
    audio_file.write_bytes(b"existing audio")

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

    service = NoDownloadService(storage_root=str(tmp_path))

    result = service.download_videos(db, ["video-1"])
    video = db.query(Video).filter(Video.youtube_video_id == "video-1").one()

    assert result["prepared_count"] == 1
    assert result["downloaded_count"] == 0
    assert result["reused_count"] == 1
    assert result["failed_count"] == 0
    assert video.download_status == "DOWNLOADED"
    assert video.processing_status == "WAITING_CLIPS"
    assert video.local_path == "raw_videos/video-1.mp4"
    assert video.local_audio_path == "wav/video-1.wav"
