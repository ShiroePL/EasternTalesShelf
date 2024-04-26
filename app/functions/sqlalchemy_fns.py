# Imports
from datetime import datetime
import json
from sqlalchemy import exc
from app.functions.class_mangalist import engine, Base, MangaList, db_session
from app.config import is_development_mode

# Initialize the database
def initialize_database():
    """ Initialize the database by creating all tables. """
    Base.metadata.create_all(bind=engine)

# Fetch manga list with proper session management
def get_manga_list_alchemy():
    """ Fetch manga list, managing sessions with scoped_session. """
    try:
        manga_list = db_session.query(MangaList).order_by(MangaList.last_updated_on_site.desc()).all()
        return [parse_timestamp(manga) for manga in manga_list]
    except Exception as e:
        print("Error while fetching from the database:", e)
        db_session.rollback()
        return []
    finally:
        db_session.remove()  # Correct usage of remove()

# Parse timestamps for manga entries
def parse_timestamp(manga):
    """ Parse timestamps for manga entries. """
    manga_dict = {column.name: getattr(manga, column.name) for column in manga.__table__.columns}
    manga_dict['last_updated_on_site'] = manga_dict.get('last_updated_on_site', datetime(1900, 1, 1))
    return manga_dict

# Update cover download status in bulk
def update_cover_download_status_bulk(ids_to_download, status):
    """ Update the download status for a bulk of manga entries using scoped_session. """
    try:
        db_session.query(MangaList).filter(MangaList.id_anilist.in_(ids_to_download)).update({"is_cover_downloaded": status}, synchronize_session='fetch')
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print("Error updating cover download statuses:", e)
    finally:
        db_session.remove()

def update_manga_links(id_anilist, bato_link, extracted_links):
    """Update manga entry with Bato and MangaUpdates links."""
    try:
        # Use db_session to access the scoped session
        manga_entry = db_session.query(MangaList).filter_by(id_anilist=id_anilist).first()
        if manga_entry:
            manga_entry.bato_link = bato_link

            # Convert existing links to a list if stored as a string
            existing_links = eval(manga_entry.external_links) if manga_entry.external_links else []

            # Add new MangaUpdates links if they're not already in the existing links
            new_links = [link for link in extracted_links if link not in existing_links]
            updated_links = existing_links + new_links

            # Ensure links are stored with double quotes
            manga_entry.external_links = json.dumps(updated_links)  # This will store list with double quotes

            db_session.commit()
        else:
            print("Manga entry not found for AniList ID:", id_anilist)
    except exc.SQLAlchemyError as e:
        db_session.rollback()
        print("Error updating manga links:", e)
    finally:
        db_session.remove()  # Properly remove the session from the scoped_session registry

# Ensure the database is initialized on module import
initialize_database()
