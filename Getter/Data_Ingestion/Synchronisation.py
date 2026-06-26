from datetime import datetime, timezone

from sqlalchemy.orm import Session

from Data_Ingestion.Youtube_service import YoutubeService
from Data_Ingestion.models import Channel, Video


class SyncService:
    MIN_VIDEO_DURATION_SECONDS = 180

    def __init__(self):
        self.youtube_service = YoutubeService()

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        # Mettre les dates dans un format comparable, avec ou sans fuseau horaire.
        if value is None:
            return None

        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)

        return value

    def _parse_published_at(self, published_at: str | None) -> datetime | None:
        if not published_at:
            return None

        return self._normalize_datetime(
            datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        )

    def _is_long_video(self, video_data: dict) -> bool:
        duration_seconds = video_data.get("duration_seconds")
        return duration_seconds is not None and duration_seconds >= self.MIN_VIDEO_DURATION_SECONDS

    def _select_valid_videos(
        self,
        youtube_videos: list[dict],
        max_new_videos: int | None = None,
    ) -> list[dict]:
        # Parcourir les vidéos de la plus récente à la plus ancienne,
        # ignorer celles de moins de 3 minutes, puis s'arrêter quand on a assez de vidéos valides.
        selected_videos = []

        for video_data in youtube_videos:
            if not self._is_long_video(video_data):
                continue

            selected_videos.append(video_data)

            if max_new_videos is not None and len(selected_videos) >= max_new_videos:
                break

        return selected_videos

    def _latest_valid_video(self, youtube_videos: list[dict]) -> dict | None:
        for video_data in youtube_videos:
            if self._is_long_video(video_data):
                return video_data

        return None

    def _upsert_channel(self, db: Session, channel_info: dict) -> Channel:
        # Créer la chaîne si elle n'existe pas encore, sinon mettre à jour ses informations.
        channel = db.query(Channel).filter(
            Channel.channel_id == channel_info["channel_id"]
        ).first()

        if channel is None:
            channel = Channel(**channel_info)
            db.add(channel)
        else:
            channel.channel_name = channel_info["channel_name"]
            channel.channel_url = channel_info["channel_url"]
            channel.uploads_playlist_id = channel_info["uploads_playlist_id"]

        return channel

    def _finalize_channel(
        self,
        db: Session,
        channel: Channel,
        channel_info: dict,
        latest_download: datetime | None,
    ) -> None:
        # Enregistrer l'état résumé de la chaîne après la synchronisation.
        channel.youtube_video_count = channel_info["youtube_video_count"]
        channel.db_video_count = db.query(Video).filter(
            Video.channel_db_id == channel.id
        ).count()
        channel.latest_download = latest_download
        channel.last_sync_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def ingest_channel(
        self,
        db: Session,
        channel_url: str,
        max_new_videos: int | None = None,
    ):
        # Ici, max_new_videos compte seulement les vidéos valides, pas les shorts ignorés.
        if max_new_videos is not None and max_new_videos < 0:
            raise ValueError("max_new_videos must be greater than or equal to 0")

        channel_info = self.youtube_service.get_channel_info(channel_url)
        channel = self._upsert_channel(db, channel_info)
        db.flush()

        if max_new_videos == 0:
            # Mettre à jour la chaîne, mais ne préparer aucun téléchargement.
            latest_videos = self.youtube_service.get_channel_videos(
                channel.uploads_playlist_id,
            )
            latest_video = self._latest_valid_video(latest_videos)
            latest_download = (
                self._parse_published_at(latest_video["published_at"])
                if latest_video is not None
                else channel.latest_download
            )

            db.flush()
            self._finalize_channel(db, channel, channel_info, latest_download)
            db.commit()

            return {
                "channel_name": channel.channel_name,
                "youtube_video_count": channel.youtube_video_count,
                "videos_in_database": channel.db_video_count,
                "latest_download": channel.latest_download,
                "new_videos_found": 0,
                "new_videos": [],
                "new_video_ids": [],
                "download_video_ids": [],
            }

        youtube_videos = self.youtube_service.get_channel_videos(
            channel.uploads_playlist_id,
        )
        # Garder uniquement les vidéos longues, puis limiter le nombre de vidéos retenues si demandé.
        youtube_videos = self._select_valid_videos(
            youtube_videos,
            max_new_videos=max_new_videos,
        )
        selected_video_ids = [
            video_data["youtube_video_id"]
            for video_data in youtube_videos
        ]

        existing_video_ids = {
            video.youtube_video_id
            for video in db.query(Video).filter(
                Video.channel_db_id == channel.id
            ).all()
        }

        new_videos = []
        new_video_ids = []

        for video_data in youtube_videos:
            published_at = self._parse_published_at(video_data["published_at"])

            if published_at is None:
                continue

            if video_data["youtube_video_id"] not in existing_video_ids:
                db.add(Video(
                    channel_db_id=channel.id,
                    youtube_video_id=video_data["youtube_video_id"],
                    title=video_data["title"],
                    published_at=published_at,
                    youtube_url=video_data["youtube_url"],
                ))
                new_videos.append(video_data)
                new_video_ids.append(video_data["youtube_video_id"])

        latest_video = self._latest_valid_video(youtube_videos)
        latest_download = (
            self._parse_published_at(latest_video["published_at"])
            if latest_video is not None
            else channel.latest_download
        )

        db.flush()
        self._finalize_channel(db, channel, channel_info, latest_download)
        db.commit()

        return {
            "channel_name": channel.channel_name,
            "youtube_video_count": channel.youtube_video_count,
            "videos_in_database": channel.db_video_count,
            "latest_download": channel.latest_download,
            "new_videos_found": len(new_videos),
            "new_videos": new_videos,
            "new_video_ids": new_video_ids,
            "download_video_ids": selected_video_ids,
        }

    def refresh_channel(self, db: Session, channel_url: str):
        channel_info = self.youtube_service.get_channel_info(channel_url)
        channel = self._upsert_channel(db, channel_info)
        channel_was_created = channel.id is None
        db.flush()

        latest_videos = self.youtube_service.get_channel_videos(
            channel.uploads_playlist_id,
        )
        # Le scheduler ne garde que la vidéo la plus récente qui n'est pas un short.
        latest_video = self._latest_valid_video(latest_videos)

        latest_download = self._parse_published_at(
            latest_video["published_at"]
        ) if latest_video else channel.latest_download
        previous_latest_download = self._normalize_datetime(channel.latest_download)

        download_video_ids = []
        new_videos = []

        if latest_video is not None and not channel_was_created:
            if previous_latest_download is not None and latest_download > previous_latest_download:
                existing_video = db.query(Video).filter(
                    Video.channel_db_id == channel.id,
                    Video.youtube_video_id == latest_video["youtube_video_id"],
                ).first()

                if existing_video is None:
                    db.add(Video(
                        channel_db_id=channel.id,
                        youtube_video_id=latest_video["youtube_video_id"],
                        title=latest_video["title"],
                        published_at=latest_download,
                        youtube_url=latest_video["youtube_url"],
                    ))
                    new_videos.append(latest_video)

                download_video_ids.append(latest_video["youtube_video_id"])
            elif previous_latest_download is None:
                latest_download = latest_download

        db.flush()
        self._finalize_channel(db, channel, channel_info, latest_download)
        db.commit()

        return {
            "channel_name": channel.channel_name,
            "youtube_video_count": channel.youtube_video_count,
            "videos_in_database": channel.db_video_count,
            "latest_download": channel.latest_download,
            "new_videos_found": len(new_videos),
            "new_videos": new_videos,
            "new_video_ids": download_video_ids,
            "download_video_ids": download_video_ids,
            "channel_created": channel_was_created,
        }
