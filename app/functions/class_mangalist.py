import os
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Text, Boolean, create_engine, ForeignKey
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from werkzeug.security import check_password_hash
from app.config import DATABASE_URI
from sqlalchemy.sql import text


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
    

class MangaUpdatesDetails(Base):
    __tablename__ = 'mangaupdates_details'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anilist_id = Column(Integer, nullable=False)
    status = Column(Text, nullable=True)
    licensed = Column(Boolean, nullable=True)
    completed = Column(Boolean, nullable=True)
    last_updated_timestamp = Column(Text, nullable=True)

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