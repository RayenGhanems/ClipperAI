import os
from dotenv import load_dotenv
from pytubefix import YouTube
from sqlalchemy.orm import Session
from moviepy import VideoFileClip
from Data_Ingestion.models import Video
load_dotenv()

class DownloadService:

    def __init__(self, storage_root: str | None = None, output_dir: str | None = None):
        self.storage_root = storage_root or os.getenv("STORAGE_ROOT", "storage")
        self.output_dir = output_dir or os.path.join(self.storage_root, "raw_videos")
        os.makedirs(self.output_dir, exist_ok=True)

    def to_relative_path(self, path: str) -> str:
        return os.path.relpath(path, self.storage_root).replace(os.sep, "/")

    def download_video(self, video: Video) -> str:
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

        filename = f"{video.youtube_video_id}.mp4"

        saved_path = stream.download(
            output_path=self.output_dir,
            filename=filename
        )

        return saved_path
    
    def extract_audio(self, video_path: str) -> str:

        wav_dir = os.path.join(self.storage_root, "wav")
        os.makedirs(wav_dir, exist_ok=True)

        video_id = os.path.splitext(
        os.path.basename(video_path)
    )[0]

        audio_path = os.path.join(
        wav_dir,
        f"{video_id}.wav"
    )

        video = VideoFileClip(video_path)

        try:
            video.audio.write_audiofile(
            audio_path,
            codec="pcm_s16le"
        )
        finally:
            video.close()

        return audio_path
    


    def download_pending_videos(self, db: Session):
        
        pending_videos = db.query(Video).filter(
            Video.download_status == "PENDING"
        ).all()

        downloaded = []
        failed = []
        
        for video in pending_videos:
            try:
                local_path = self.download_video(video)
                audio_path = self.extract_audio(local_path)

                video.local_path = self.to_relative_path(local_path)
                video.local_audio_path = self.to_relative_path(audio_path)
                video.download_status = "DOWNLOADED"
                video.processing_status = "WAITING_CLIPS"

                downloaded.append({
                    "id": video.id,
                    "title": video.title,
                    "local_path": video.local_path,
                    "local_audio_path": video.local_audio_path
                })

            except Exception as e:
                video.download_status = "FAILED"

                failed.append({
                    "id": video.id,
                    "title": video.title,
                    "error": str(e)
                })

        db.commit()

        return {
            "downloaded_count": len(downloaded),
            "failed_count": len(failed),
            "downloaded": downloaded,
            "failed": failed
        }
    
