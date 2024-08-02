# Imports
from datetime import datetime
import json
import re
from sqlalchemy import exc
from app.functions.class_mangalist import engine, Base, MangaList, db_session, MangaUpdatesDetails
from app.config import is_development_mode
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

def get_manga_details_alchemy():
    """ Fetch manga details, managing sessions with scoped_session. """
    try:
        manga_details_list = db_session.query(MangaUpdatesDetails).all()
        return manga_details_list
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
            print("Existing links:", existing_links)
            # Add new MangaUpdates links if they're not already in the existing links
            new_links = [link for link in extracted_links if link not in existing_links]
            updated_links = existing_links + new_links
            print("Updated links:", updated_links)
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


def save_manga_details(details, anilist_id):
    try:
        series_id = details.get("series_id")
        manga_detail = db_session.query(MangaUpdatesDetails).filter_by(series_id=series_id).first()

        last_updated_timestamp = details.get("last_updated", {}).get("timestamp")
        if last_updated_timestamp:
            last_updated_timestamp = datetime.fromtimestamp(last_updated_timestamp)
        
        status = details.get("status", "")
        # Replace multiple \n characters with a single \n
        status = re.sub(r'\n+', '\n', status)

        if not manga_detail:
            manga_detail = MangaUpdatesDetails(
                series_id=series_id,
                anilist_id=anilist_id,
                status=status,
                licensed=details.get("licensed"),
                completed=details.get("completed"),
                last_updated_timestamp=last_updated_timestamp
            )
            db_session.add(manga_detail)
        else:
            manga_detail.status = status
            manga_detail.licensed = details.get("licensed")
            manga_detail.completed = details.get("completed")
            manga_detail.last_updated_timestamp = last_updated_timestamp
            manga_detail.anilist_id = anilist_id

        db_session.commit()
        logging.info(f"Saved to table: {manga_detail}")
        logging.info("Manga details saved successfully.")
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error saving manga details: {e}")
    finally:
        db_session.remove()

# Ensure the database is initialized on module import
initialize_database()
