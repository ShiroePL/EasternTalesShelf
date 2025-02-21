from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.functions.class_mangalist import Base

class ScrapeQueue(Base):
    __tablename__ = "scraping_queue"

    id = Column(Integer, primary_key=True)
    manhwa_title = Column(String(255), nullable=False)
    bato_url = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")
    current_chapter = Column(Integer, default=0)
    total_chapters = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    priority = Column(Integer, default=0)
    anilist_id = Column(Integer, nullable=True)

class ManhwaDownloadStatus(Base):
    __tablename__ = "manhwa_download_status"

    id = Column(Integer, primary_key=True)
    anilist_id = Column(Integer, unique=True, nullable=False)
    download_status = Column(String(50), default="not_downloaded")
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 