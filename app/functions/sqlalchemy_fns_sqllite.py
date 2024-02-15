from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, TIMESTAMP, Text, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
# from config import Config  # This import might not be needed for SQLite configuration

Base = declarative_base()

class MangaList(Base):
    __tablename__ = 'manga_list'
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
    bato_link = Column(Text, default='')  # Adjust types and column names as necessary


def initialize_database():
    engine = get_engine()
    Base.metadata.create_all(engine)
def get_engine():
    # For SQLite, the connection string is simply 'sqlite:///path_to_your_database.db'
    return create_engine('sqlite:///anilist_db.db')

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def get_manga_list_alchemy(testing=False):
    session = get_session()
    
    try:
        
        manga_list_query = session.query(MangaList).order_by(MangaList.last_updated_on_site.desc())

        manga_list = manga_list_query.all()

        # Convert to a list of dictionaries (if needed) and handle None values in dates
        def parse_timestamp(manga):
            manga_dict = {column.name: getattr(manga, column.name) for column in manga.__table__.columns}
            manga_dict['last_updated_on_site'] = manga_dict.get('last_updated_on_site', datetime(1900, 1, 1))
            return manga_dict

        manga_list = [parse_timestamp(manga) for manga in manga_list]

        return manga_list

    except Exception as e:
        print("Error while fetching from the database", e)
        return []
    finally:
        session.close()

def add_bato_link(id_anilist, bato_link):
    session = get_session()

    try:
        manga_entry = session.query(MangaList).filter_by(id_anilist=id_anilist).first()
        if manga_entry:
            manga_entry.bato_link = bato_link
            session.commit()
        else:
            print("Manga entry not found for AniList ID:", id_anilist)
    except exc.SQLAlchemyError as e:
        print("Error updating 'bato_link':", e)
    finally:
        session.close()

initialize_database()