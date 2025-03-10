import os
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Text, Boolean, create_engine, ForeignKey, JSON, DateTime
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from werkzeug.security import check_password_hash
from app.config import DATABASE_URI
from sqlalchemy.sql import text
from datetime import datetime


engine = create_engine(DATABASE_URI, pool_recycle=3600, pool_pre_ping=True, echo=False)  # Recycles connections after one hour
session_maker = sessionmaker(bind=engine)

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

is_development = os.getenv('FLASK_ENV')

class MangaList(Base):
    __tablename__ = 'manga_list'  # Always use production table
    id_default = Column(Integer, primary_key=True, autoincrement=True)
    id_anilist = Column(Integer, nullable=False)
    id_mal = Column(Integer)
    title_english = Column(String(255))
    title_romaji = Column(String(255))
    on_list_status = Column(String(255))
    status = Column(String(255))
    media_format = Column(String(255))
    all_chapters = Column(Integer, default=0)
    all_volumes = Column(Integer, default=0)
    chapters_progress = Column(Integer, default=0)
    volumes_progress = Column(Integer, default=0)
    score = Column(Float, default=0)
    reread_times = Column(Integer, default=0)
    cover_image = Column(String(255))
    is_cover_downloaded = Column(Boolean, default=False)
    is_favourite = Column(Integer, default=0)
    anilist_url = Column(String(255))
    mal_url = Column(String(255))
    last_updated_on_site = Column(TIMESTAMP)
    entry_createdAt = Column(TIMESTAMP)
    user_startedAt = Column(Text, default='not started')
    user_completedAt = Column(Text, default='not completed')
    notes = Column(Text)
    description = Column(Text)
    country_of_origin = Column(String(255))
    media_start_date = Column(Text, default='media not started')
    media_end_date = Column(Text, default='media not ended')
    genres = Column(Text, default='none genres provided')
    external_links = Column(Text, default='none links associated')
    bato_link = Column(Text, default='')

    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)

class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)

class MangaUpdatesDetails(Base):
    __tablename__ = 'mangaupdates_details'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, nullable=False)
    status = Column(Text, nullable=True)
    licensed = Column(Boolean, nullable=True)
    completed = Column(Boolean, nullable=True)
    last_updated_timestamp = Column(Text, nullable=True)

    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)

class MangaStatusNotification(Base):
    __tablename__ = 'manga_status_notifications'  # Always use production table
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, ForeignKey('manga_list.id_anilist'), nullable=False)  # Always reference production manga_list
    title = Column(String(255), nullable=False)
    notification_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    old_status = Column(Text)
    new_status = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    is_read = Column(Boolean, default=False)
    importance = Column(Integer, default=1)
    url = Column(String(255))

    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)

class AnilistNotification(Base):
    __tablename__ = 'anilist_notifications'

    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, unique=True)  # AniList's notification ID
    type = Column(String(50))  # The notification type (e.g., AIRING, RELATED_MEDIA_ADDITION, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Common optional fields
    user_name = Column(String(255), nullable=True)  # For notifications involving users
    context = Column(Text, nullable=True)  # For notifications with context
    
    # Media related fields
    media_title = Column(String(255), nullable=True)  # For notifications involving media
    media_id = Column(Integer, nullable=True)  # AniList media ID if applicable
    
    # Specific fields
    episode = Column(Integer, nullable=True)  # For AiringNotification
    reason = Column(Text, nullable=True)  # For MediaDataChangeNotification, MediaMergeNotification
    deleted_media_title = Column(String(255), nullable=True)  # For MediaDeletionNotification
    
    # Additional metadata
    is_read = Column(Boolean, default=False)
    extra_data = Column(JSON, nullable=True)  # Store any additional fields as JSON
    
    def __repr__(self):
        return f"<AnilistNotification(id={self.id}, type={self.type}, created_at={self.created_at})>"
    
    @classmethod
    def create_table_if_not_exists(cls, engine):
        """Create the table if it doesn't exist"""
        if not engine.dialect.has_table(engine, cls.__tablename__):
            cls.__table__.create(engine)

def init_db():
    """Initialize the database"""
    Base.metadata.create_all(bind=engine)
    
    # Create tables if they don't exist
    MangaList.create_table_if_not_exists(engine)
    MangaUpdatesDetails.create_table_if_not_exists(engine)
    Users.create_table_if_not_exists(engine)
    MangaStatusNotification.create_table_if_not_exists(engine)
    AnilistNotification.create_table_if_not_exists(engine)