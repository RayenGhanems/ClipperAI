from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from Data_Ingestion.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, default="youtube")
    channel_id = Column(String, unique=True, nullable=False)
    channel_name=Column(String)
    channel_url = Column(String)
    uploads_playlist_id = Column(String)
    youtube_video_count = Column(Integer, default=0)
    db_video_count = Column(Integer, default=0)
    last_sync_at = Column(DateTime)

    videos = relationship("Video", back_populates="channel")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    channel_db_id = Column(Integer, ForeignKey("channels.id"))

    youtube_video_id = Column(String, nullable=False)
    title = Column(String)
    published_at = Column(DateTime)
    youtube_url = Column(String)
    local_path = Column(String)
    local_audio_path = Column(String)

    download_status = Column(String, default="PENDING")
    processing_status = Column(String, default="WAITING_DOWNLOAD")

    created_at = Column(DateTime, default=datetime.utcnow)

    channel = relationship("Channel", back_populates="videos")

    __table_args__ = (
        UniqueConstraint("channel_db_id", "youtube_video_id", name="unique_channel_video"),
    )


