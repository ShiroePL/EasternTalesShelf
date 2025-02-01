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

def fetch_all_records():
    """ Fetch all records from the database. """
    try:
        all_records = db_session.query(MangaList).all()
        return all_records
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
            
            # Create a set of existing links for O(1) lookup
            existing_links_set = set(existing_links)
            
            # Only add new links that aren't already in the set
            new_links = []
            for link in extracted_links:
                if link not in existing_links_set:
                    new_links.append(link)
                    existing_links_set.add(link)  # Add to set to prevent duplicates within extracted_links
            
            # Combine existing and new links
            updated_links = existing_links + new_links
            print("Updated links:", updated_links)
            
            # Ensure links are stored with double quotes
            manga_entry.external_links = json.dumps(updated_links)

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
        

        # Query by anilist_id instead of series_id
        manga_detail = db_session.query(MangaUpdatesDetails).filter_by(anilist_id=anilist_id).first()

        # Extract and clean the status
        status = details.get('status_in_country_of_origin', '')
        status = re.sub(r'\n+', '\n', status)  # Replace multiple \n characters with a single \n

        # Convert "Yes" and "No" into boolean values for licensed and completed
        licensed_value = details.get('licensed_in_english', '').lower()
        completed_value = details.get('completely_scanlated', '').lower()

        licensed = licensed_value == 'yes'  # True if 'Yes', else False
        completed = completed_value == 'yes'  # True if 'Yes', else False

        # Extract and convert the last_updated timestamp
        last_updated_timestamp = details.get('last_updated', '')


        # If no entry exists, create a new one
        if not manga_detail:
            manga_detail = MangaUpdatesDetails(
                anilist_id=anilist_id,
                status=status,
                licensed=licensed,
                completed=completed,
                last_updated_timestamp=last_updated_timestamp
            )
            db_session.add(manga_detail)
        else:
            # Update the existing record with new data
            manga_detail.status = status
            manga_detail.licensed = licensed
            manga_detail.completed = completed
            manga_detail.last_updated_timestamp = last_updated_timestamp

        # Commit the transaction to save changes
        db_session.commit()
        
        logging.info(f"Manga details saved successfully. Details: status: {status}, licensed: {licensed}, completed: {completed}, last_updated: {last_updated_timestamp}")
    except Exception as e:
        # Rollback in case of an error
        db_session.rollback()
        logging.error(f"Error saving manga details: {e}")
    finally:
        # Close the session
        db_session.remove()




# Ensure the database is initialized on module import
initialize_database()
