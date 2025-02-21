# Imports
from datetime import datetime
import json
import re
from sqlalchemy import exc, update, desc, func
from app.functions.class_mangalist import engine, Base, MangaList, db_session, MangaUpdatesDetails
from app.config import is_development_mode
import logging
from app.models.scraper_models import ScrapeQueue, ManhwaDownloadStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Initialize the database
def initialize_database():
    """Initialize the database by creating all tables and initial data."""
    Base.metadata.create_all(bind=engine)
    initialize_download_status()

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
            # Only update bato_link if one is provided
            if bato_link is not None:
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

# Add these new functions for queue management
def pause_queue_task(title):
    """Update task status to stopped."""
    try:
        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if not task:
            return False

        # Update scraping queue status
        task.status = "stopped"

        # Update download status if anilist_id exists
        if task.anilist_id:
            status_entry = db_session.query(ManhwaDownloadStatus)\
                .filter_by(anilist_id=task.anilist_id)\
                .first()
            
            if status_entry:
                status_entry.download_status = "stopped"
            else:
                new_status = ManhwaDownloadStatus(
                    anilist_id=task.anilist_id,
                    download_status="stopped"
                )
                db_session.add(new_status)

        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error pausing task: {e}")
        raise

def resume_queue_task(title):
    """Update task status back to pending."""
    try:
        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if not task:
            return False

        task.status = "pending"

        if task.anilist_id:
            status_entry = db_session.query(ManhwaDownloadStatus)\
                .filter_by(anilist_id=task.anilist_id)\
                .first()
            
            if status_entry:
                status_entry.download_status = "pending"
            else:
                new_status = ManhwaDownloadStatus(
                    anilist_id=task.anilist_id,
                    download_status="pending"
                )
                db_session.add(new_status)

        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error resuming task: {e}")
        raise

def remove_queue_task(title):
    """Delete task from queue."""
    try:
        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if not task:
            return False

        # Update download status to NOT_DOWNLOADED if anilist_id exists
        if task.anilist_id:
            db_session.execute(
                update(ManhwaDownloadStatus)
                .where(ManhwaDownloadStatus.anilist_id == task.anilist_id)
                .values(download_status="NOT_DOWNLOADED")
            )

        # Remove from scraping queue
        db_session.delete(task)
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error removing task: {e}")
        raise

def force_task_priority(title):
    """Update task priority to highest + 1."""
    try:
        # Use sqlalchemy.func instead of db_session.func
        max_priority = db_session.query(func.max(ScrapeQueue.priority)).scalar() or 0
        
        db_session.execute(
            update(ScrapeQueue)
            .where(ScrapeQueue.manhwa_title == title)
            .values(
                priority=max_priority + 1,
                status="pending"
            )
        )
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error updating priority: {e}")
        raise

def add_to_queue(title, bato_url, anilist_id=None):
    """Add or update task in queue."""
    try:
        existing_task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        
        if existing_task:
            existing_task.status = "pending"
            existing_task.error_message = None
            existing_task.bato_url = bato_url
            existing_task.anilist_id = anilist_id
            existing_task.current_chapter = 0
            existing_task.total_chapters = 0
            existing_task.started_at = None
            existing_task.completed_at = None
            # Keep the original created_at
            # Update priority to be higher than current max
            max_priority = db_session.query(func.max(ScrapeQueue.priority)).scalar() or 0
            existing_task.priority = max_priority + 1
        else:
            # Get highest priority and add 1
            max_priority = db_session.query(func.max(ScrapeQueue.priority)).scalar() or 0
            new_task = ScrapeQueue(
                manhwa_title=title,
                bato_url=bato_url,
                anilist_id=anilist_id,
                status="pending",
                current_chapter=0,
                total_chapters=0,
                error_message=None,
                created_at=datetime.utcnow(),
                started_at=None,
                completed_at=None,
                priority=max_priority + 1
            )
            db_session.add(new_task)

        # Update download status to pending
        if anilist_id:
            status_entry = db_session.query(ManhwaDownloadStatus)\
                .filter_by(anilist_id=anilist_id)\
                .first()
            
            if status_entry:
                status_entry.download_status = "pending"
            else:
                new_status = ManhwaDownloadStatus(
                    anilist_id=anilist_id,
                    download_status="pending"
                )
                db_session.add(new_status)

        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error adding task to queue: {e}")
        raise

def get_queue_status():
    """Get current queue status including current and pending tasks."""
    try:
        current_task = db_session.query(ScrapeQueue)\
            .filter(ScrapeQueue.status == "in_progress")\
            .order_by(ScrapeQueue.started_at.desc())\
            .first()
            
        pending_tasks = db_session.query(ScrapeQueue)\
            .filter(ScrapeQueue.status.in_(["pending", "stopped"]))\
            .order_by(ScrapeQueue.priority.desc(), ScrapeQueue.created_at.asc())\
            .all()

        return current_task, pending_tasks
    except Exception as e:
        logging.error(f"Error getting queue status: {e}")
        raise

# Add this function to initialize download status table
def initialize_download_status():
    """Initialize download status for all manga entries."""
    try:
        # Get all manga entries that don't have a download status
        manga_entries = db_session.query(MangaList.id_anilist).all()
        existing_statuses = db_session.query(ManhwaDownloadStatus.anilist_id).all()
        
        # Convert to sets for faster lookup
        existing_ids = {status[0] for status in existing_statuses}
        manga_ids = {entry[0] for entry in manga_entries}
        
        # Find manga entries that need status initialization
        missing_ids = manga_ids - existing_ids
        
        # Create new status entries for missing manga
        for anilist_id in missing_ids:
            new_status = ManhwaDownloadStatus(
                anilist_id=anilist_id,
                download_status="NOT_DOWNLOADED"
            )
            db_session.add(new_status)
        
        db_session.commit()
        logging.info(f"Initialized download status for {len(missing_ids)} manga entries")
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error initializing download status: {e}")
    finally:
        db_session.remove()

# Add these functions for managing download status
def get_download_statuses():
    """Get download status for all manga by checking both tables."""
    try:
        download_statuses = db_session.query(ManhwaDownloadStatus).all()
        status_dict = {status.anilist_id: status for status in download_statuses}

        queue_entries = db_session.query(ScrapeQueue).all()
        
        for entry in queue_entries:
            if entry.anilist_id:
                if entry.status == "in_progress":
                    queue_status = "in_progress"
                elif entry.status == "pending":
                    queue_status = "pending"
                elif entry.status == "stopped":
                    queue_status = "stopped"
                else:
                    queue_status = "not_downloaded"

                if entry.anilist_id in status_dict:
                    status_dict[entry.anilist_id].download_status = queue_status
                else:
                    new_status = ManhwaDownloadStatus(
                        anilist_id=entry.anilist_id,
                        download_status=queue_status
                    )
                    status_dict[entry.anilist_id] = new_status

        return [{'anilist_id': status.anilist_id, 'status': status.download_status} 
                for status in status_dict.values()]
    except Exception as e:
        logging.error(f"Error getting download statuses: {e}")
        return []

def update_download_status(anilist_id, new_status):
    """Update download status for a specific manga."""
    try:
        status_entry = db_session.query(ManhwaDownloadStatus)\
            .filter_by(anilist_id=anilist_id)\
            .first()
        
        if status_entry:
            status_entry.download_status = new_status.lower()
        else:
            status_entry = ManhwaDownloadStatus(
                anilist_id=anilist_id,
                download_status=new_status.lower()
            )
            db_session.add(status_entry)
            
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error updating download status: {e}")
        raise

# Ensure the database is initialized on module import
initialize_database()
