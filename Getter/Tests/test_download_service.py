import os

from Data_Ingestion.download import DownloadService


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
