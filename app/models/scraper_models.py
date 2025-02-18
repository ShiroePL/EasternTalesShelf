import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text
from app.functions.class_mangalist import Base

class ScrapingStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class ScrapeQueue(Base):
    __tablename__ = "scraping_queue"

    id = Column(Integer, primary_key=True)
    manhwa_title = Column(String(255), nullable=False)
    bato_url = Column(String(500), nullable=False)
    status = Column(Enum(ScrapingStatus), default=ScrapingStatus.PENDING)
    current_chapter = Column(Integer, default=0)
    total_chapters = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    priority = Column(Integer, default=0)
    anilist_id = Column(Integer, nullable=True)

class DownloadStatus(enum.Enum):
    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    PENDING = "pending"
    COMPLETED = "completed"

class ManhwaDownloadStatus(Base):
    __tablename__ = "manhwa_download_status"

    id = Column(Integer, primary_key=True)
    anilist_id = Column(Integer, unique=True, nullable=False)
    download_status = Column(Enum(DownloadStatus), default=DownloadStatus.NOT_DOWNLOADED)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 