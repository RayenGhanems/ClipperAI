from datetime import datetime
from Data_Ingestion.Youtube_service import YoutubeService
from sqlalchemy.orm import Session
from Data_Ingestion.models import Channel,Video

class SyncService:
    def __init__(self):
        self.youtube_service=YoutubeService()

    def sync_channel(self, db:Session, channel_url:str):
        channel_info=self.youtube_service.get_channel_info(channel_url)
        channel = db.query(Channel).filter(
            Channel.channel_id == channel_info["channel_id"]
        ).first()

        if channel is None:
            channel =Channel(**channel_info)
            db.add(channel)
            db.commit()
            db.refresh(channel)

        youtube_videos= self.youtube_service.get_channel_videos(
            channel.uploads_playlist_id

        )    

        existing_videos_ids = {
            v.youtube_video_id
            for v in db.query(Video).filter(Video.channel_db_id == channel.id).all()
        }

        new_videos=[]

        for video_data in youtube_videos:
            if video_data["youtube_video_id"] not in existing_videos_ids:
                video = Video(
                    channel_db_id=channel.id,
                    youtube_video_id= video_data["youtube_video_id"],
                    title=video_data["title"],
                    published_at=datetime.fromisoformat(
                        video_data["published_at"].replace("Z", "+00:00")
                    ),
                    youtube_url=video_data["youtube_url"],
                )
                db.add(video)
                new_videos.append(video_data)

        channel.youtube_video_count =  channel_info["youtube_video_count"]
        channel.db_video_count = db.query(Video).filter(Video.channel_db_id == channel.id).count()+len(new_videos)
        channel.last_sync_at = datetime.utcnow()

        db.commit()

        return {
            "channel_name": channel.channel_name,
            "youtube_video_count": channel.youtube_video_count,
            "videos_in_database": channel.db_video_count,
            "new_videos_found": len(new_videos),
            "new_videos": new_videos,
        }
    
