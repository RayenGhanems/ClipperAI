from sqlalchemy.orm import Session

from Data_Ingestion.Synchronisation import SyncService
from Data_Ingestion.download import DownloadService
from Data_Ingestion.models import Channel, Video


class PipelineService:

    def __init__(self):
        self.sync_service = SyncService()
        self.download_service = DownloadService()

    def sync_and_download_channel(self, db: Session, channel_url: str):
        sync_result = self.sync_service.sync_channel(db, channel_url)

        pending_videos = db.query(Video).filter(
            Video.download_status == "PENDING"
        ).all()

        download_result = self.download_service.download_pending_videos(db)

        return {
            "sync_result": sync_result,
            "pending_videos_before_download": len(pending_videos),
            "download_result": download_result
        }

    def sync_existing_channels(self, db: Session):
        channels = db.query(Channel).all()

        synced_channels = []
        skipped_channels = []
        failed_channels = []

        for channel in channels:
            channel_data = {
                "channel_db_id": channel.id,
                "channel_name": channel.channel_name,
                "channel_url": channel.channel_url,
            }

            if not channel.channel_url:
                skipped_channels.append({
                    **channel_data,
                    "reason": "missing_channel_url",
                })
                continue

            try:
                sync_result = self.sync_service.sync_channel(
                    db,
                    channel.channel_url
                )

                synced_channels.append({
                    **channel_data,
                    "sync_result": sync_result,
                })

            except Exception as e:
                db.rollback()
                failed_channels.append({
                    **channel_data,
                    "error": str(e),
                })

        return {
            "total_channels": len(channels),
            "synced_count": len(synced_channels),
            "skipped_count": len(skipped_channels),
            "failed_count": len(failed_channels),
            "synced_channels": synced_channels,
            "skipped_channels": skipped_channels,
            "failed_channels": failed_channels,
        }

    def sync_and_download_existing_channels(self, db: Session):
        sync_result = self.sync_existing_channels(db)

        pending_videos_count = db.query(Video).filter(
            Video.download_status == "PENDING"
        ).count()

        download_result = self.download_service.download_pending_videos(db)

        return {
            "sync_result": sync_result,
            "pending_videos_before_download": pending_videos_count,
            "download_result": download_result,
        }
