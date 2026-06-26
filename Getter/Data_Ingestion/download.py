import os

from dotenv import load_dotenv
from moviepy import VideoFileClip
from pytubefix import YouTube
from sqlalchemy.orm import Session

from Data_Ingestion.models import Video

load_dotenv()


class DownloadService:
    def __init__(self, storage_root: str | None = None, output_dir: str | None = None):
        self.storage_root = storage_root or os.getenv("STORAGE_ROOT", "storage")
        self.output_dir = output_dir or os.path.join(self.storage_root, "raw_videos")
        os.makedirs(self.output_dir, exist_ok=True)

    def to_relative_path(self, path: str) -> str:
        return os.path.relpath(path, self.storage_root).replace(os.sep, "/")

    def to_absolute_path(self, relative_path: str) -> str:
        return os.path.join(self.storage_root, relative_path)

    def video_relative_path(self, video: Video) -> str:
        return f"raw_videos/{video.youtube_video_id}.mp4"

    def audio_relative_path(self, video: Video) -> str:
        return f"wav/{video.youtube_video_id}.wav"

    def download_video(self, video: Video) -> str:
        # Télécharger la vidéo MP4, puis extraire l'audio dans une étape séparée.
        yt = YouTube(video.youtube_url)

        stream = (
            yt.streams
            .filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )

        if stream is None:
            raise RuntimeError("Aucun stream MP4 progressif trouvé pour cette vidéo.")

        return stream.download(
            output_path=self.output_dir,
            filename=f"{video.youtube_video_id}.mp4",
        )

    def extract_audio(self, video_path: str) -> str:
        # Extraire l'audio et le stocker dans le dossier wav du stockage partagé.
        wav_dir = os.path.join(self.storage_root, "wav")
        os.makedirs(wav_dir, exist_ok=True)

        video_id = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(wav_dir, f"{video_id}.wav")

        video = VideoFileClip(video_path)

        try:
            video.audio.write_audiofile(audio_path, codec="pcm_s16le")
        finally:
            video.close()

        return audio_path

    def download_videos(self, db: Session, youtube_video_ids: list[str]):
        # Traiter uniquement les vidéos que la synchronisation a retenues.
        if not youtube_video_ids:
            return {
                "prepared_count": 0,
                "downloaded_count": 0,
                "reused_count": 0,
                "failed_count": 0,
                "prepared": [],
                "downloaded": [],
                "reused": [],
                "failed": [],
            }

        videos = db.query(Video).filter(
            Video.youtube_video_id.in_(youtube_video_ids)
        ).all()
        videos_by_id = {video.youtube_video_id: video for video in videos}

        prepared = []
        downloaded = []
        reused = []
        failed = []

        for youtube_video_id in youtube_video_ids:
            video = videos_by_id.get(youtube_video_id)

            if video is None:
                failed.append({
                    "youtube_video_id": youtube_video_id,
                    "error": "video_not_found_in_database",
                })
                continue

            try:
                # Réutiliser les fichiers déjà présents si le stockage les contient déjà.
                expected_video_path = self.to_absolute_path(
                    self.video_relative_path(video)
                )
                expected_audio_path = self.to_absolute_path(
                    self.audio_relative_path(video)
                )

                video_already_exists = os.path.exists(expected_video_path)
                audio_already_exists = os.path.exists(expected_audio_path)

                if video_already_exists:
                    local_path = expected_video_path
                else:
                    local_path = self.download_video(video)

                if audio_already_exists:
                    audio_path = expected_audio_path
                else:
                    audio_path = self.extract_audio(local_path)

                video.local_path = self.to_relative_path(local_path)
                video.local_audio_path = self.to_relative_path(audio_path)
                video.download_status = "DOWNLOADED"
                video.processing_status = "WAITING_CLIPS"

                item = {
                    "id": video.id,
                    "title": video.title,
                    "local_path": video.local_path,
                    "local_audio_path": video.local_audio_path,
                }

                prepared.append(item)

                if video_already_exists and audio_already_exists:
                    reused.append(item)
                else:
                    downloaded.append(item)

            except Exception as e:
                video.download_status = "FAILED"
                failed.append({
                    "id": video.id,
                    "title": video.title,
                    "error": str(e),
                })

        db.commit()

        return {
            "prepared_count": len(prepared),
            "downloaded_count": len(downloaded),
            "reused_count": len(reused),
            "failed_count": len(failed),
            "prepared": prepared,
            "downloaded": downloaded,
            "reused": reused,
            "failed": failed,
        }
