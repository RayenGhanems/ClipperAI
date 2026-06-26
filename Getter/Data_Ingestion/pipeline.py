from sqlalchemy.orm import Session

from Data_Ingestion.Synchronisation import SyncService
from Data_Ingestion.download import DownloadService
from Data_Ingestion.models import Channel


class PipelineService:
    def __init__(self):
        self.sync_service = SyncService()
        self.download_service = DownloadService()

    def ingest_channel(
        self,
        db: Session,
        channel_url: str,
        max_new_videos: int | None = None,
    ):
        # Point d'entrée manuel: lire une chaîne YouTube, enregistrer les vidéos valides,
        # puis télécharger seulement celles que la synchronisation a sélectionnées.
        sync_result = self.sync_service.ingest_channel(
            db,
            channel_url,
            max_new_videos=max_new_videos,
        )

        download_result = self.download_service.download_videos(
            db,
            sync_result["download_video_ids"],
        )

        return {
            "sync_result": sync_result,
            "download_result": download_result,
        }

    def refresh_channels(self, db: Session, channel_urls: list[str] | None = None):
        # Chemin utilisé par le scheduler: traiter une liste fournie, ou toutes les chaînes de la base.
        if channel_urls is None:
            channels = db.query(Channel).all()
            channel_urls = [
                channel.channel_url
                for channel in channels
                if channel.channel_url
            ]

        synced_channels = []
        failed_channels = []
        download_video_ids = []

        for channel_url in channel_urls:
            try:
                sync_result = self.sync_service.refresh_channel(db, channel_url)

                synced_channels.append({
                    "channel_url": channel_url,
                    "sync_result": sync_result,
                })
                download_video_ids.extend(sync_result["download_video_ids"])
            except Exception as e:
                failed_channels.append({
                    "channel_url": channel_url,
                    "error": str(e),
                })

        download_result = self.download_service.download_videos(
            db,
            download_video_ids,
        )

        return {
            "total_channels": len(channel_urls),
            "synced_count": len(synced_channels),
            "failed_count": len(failed_channels),
            "synced_channels": synced_channels,
            "failed_channels": failed_channels,
            "download_result": download_result,
        }
