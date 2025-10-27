"""
BatoRepository - Data Access Layer for Bato.to Notification System

Provides centralized database operations for all Bato-related tables:
- bato_manga_details
- bato_chapters
- bato_notifications
- bato_scraping_schedule
- bato_scraper_log

Uses scoped_session pattern consistent with existing codebase.

Enhanced with:
- Automatic retry logic for connection errors
- "MySQL server has gone away" error handling
- Connection pool management
"""

from typing import List, Optional, Dict, Set
from datetime import datetime
import time
from functools import wraps
from sqlalchemy import desc, and_
from sqlalchemy.exc import (
    IntegrityError, 
    OperationalError, 
    DisconnectionError,
    InterfaceError
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.functions.class_mangalist import db_session, engine
from app.models.bato_models import (
    BatoMangaDetails,
    BatoChapters,
    BatoNotifications,
    BatoScrapingSchedule,
    BatoScraperLog
)
import logging

logger = logging.getLogger(__name__)


def handle_db_connection_errors(max_retries: int = 3, initial_delay: float = 0.5):
    """
    Decorator to handle database connection errors with retry logic.
    
    Handles:
    - "MySQL server has gone away" errors
    - Connection lost errors
    - Deadlock errors
    
    Requirements:
    - 3.5: Retry logic with exponential backoff
    - 3.5: Handle "MySQL server has gone away" errors
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            delay = initial_delay
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except (OperationalError, DisconnectionError, InterfaceError) as e:
                    error_msg = str(e).lower()
                    
                    # Check if it's a connection error that should be retried
                    is_connection_error = any(phrase in error_msg for phrase in [
                        'server has gone away',
                        'lost connection',
                        'connection was killed',
                        'can\'t connect to',
                        'connection refused',
                        'deadlock'
                    ])
                    
                    if is_connection_error and retry_count < max_retries:
                        retry_count += 1
                        
                        logger.warning(
                            f"Database connection error in {func.__name__} "
                            f"(attempt {retry_count}/{max_retries}): {e}"
                        )
                        
                        # Dispose connection pool on "server has gone away"
                        if 'server has gone away' in error_msg or 'lost connection' in error_msg:
                            try:
                                engine.dispose()
                                logger.info("Connection pool disposed due to connection loss")
                            except Exception as dispose_error:
                                logger.error(f"Error disposing connection pool: {dispose_error}")
                        
                        # Rollback current transaction
                        try:
                            db_session.rollback()
                        except Exception:
                            pass
                        
                        # Exponential backoff
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                        delay = min(delay * 2, 30)  # Max 30 seconds
                    else:
                        # Not a connection error or max retries reached
                        logger.error(
                            f"Database error in {func.__name__} "
                            f"(not retrying): {e}"
                        )
                        raise
                        
                except Exception as e:
                    # Non-connection error, don't retry
                    logger.error(
                        f"Unexpected error in {func.__name__}: {e}",
                        exc_info=True
                    )
                    raise
            
            # Should not reach here, but just in case
            raise OperationalError(
                f"Failed after {max_retries} retries",
                None,
                None
            )
        
        return wrapper
    return decorator


class BatoRepository:
    """
    Centralized data access for Bato tables.
    All methods use scoped_session (db_session) for thread-safe operations.
    """
    
    # ==================== Manga Details Methods ====================
    
    @staticmethod
    @handle_db_connection_errors(max_retries=3)
    def get_manga_details(anilist_id: int) -> Optional[BatoMangaDetails]:
        """
        Get manga details by anilist_id.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            BatoMangaDetails object or None if not found
        """
        try:
            details = db_session.query(BatoMangaDetails).filter(
                BatoMangaDetails.anilist_id == anilist_id
            ).first()
            return details
        except Exception as e:
            logger.error(f"Error fetching manga details for anilist_id {anilist_id}: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.remove()
    
    @staticmethod
    @handle_db_connection_errors(max_retries=3)
    def upsert_manga_details(details_data: Dict) -> Optional[BatoMangaDetails]:
        """
        Insert or update manga details.
        Uses ON DUPLICATE KEY UPDATE for efficient upserts.
        
        Args:
            details_data: Dictionary with manga details fields
            
        Returns:
            BatoMangaDetails object or None on error
        """
        try:
            # Check if using SQLite or MySQL/MariaDB
            dialect_name = engine.dialect.name
            
            if dialect_name == 'sqlite':
                # SQLite: Use INSERT OR REPLACE
                stmt = sqlite_insert(BatoMangaDetails).values(**details_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['bato_link'],
                    set_={k: v for k, v in details_data.items() if k not in ['id', 'first_scraped_at']}
                )
                db_session.execute(stmt)
            else:
                # MySQL/MariaDB: Use INSERT ON DUPLICATE KEY UPDATE
                stmt = mysql_insert(BatoMangaDetails).values(**details_data)
                update_dict = {k: v for k, v in details_data.items() if k not in ['id', 'first_scraped_at']}
                stmt = stmt.on_duplicate_key_update(**update_dict)
                db_session.execute(stmt)
            
            db_session.commit()
            
            # Fetch and return the updated record
            result = db_session.query(BatoMangaDetails).filter(
                BatoMangaDetails.bato_link == details_data['bato_link']
            ).first()
            return result
            
        except Exception as e:
            logger.error(f"Error upserting manga details: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.remove()
    
    # ==================== Chapter Methods ====================
    
    @staticmethod
    def get_chapters(anilist_id: int, limit: Optional[int] = None) -> List[BatoChapters]:
        """
        Get all chapters for a manga, ordered by chapter_number descending.
        
        Args:
            anilist_id: AniList manga ID
            limit: Optional limit on number of chapters to return
            
        Returns:
            List of BatoChapters objects
        """
        try:
            query = db_session.query(BatoChapters).filter(
                BatoChapters.anilist_id == anilist_id
            ).order_by(desc(BatoChapters.chapter_number))
            
            if limit:
                query = query.limit(limit)
            
            chapters = query.all()
            return chapters
        except Exception as e:
            logger.error(f"Error fetching chapters for anilist_id {anilist_id}: {e}")
            db_session.rollback()
            return []
        finally:
            db_session.remove()
    
    @staticmethod
    def get_existing_chapter_ids(anilist_id: int) -> Set[str]:
        """
        Get set of bato_chapter_id already in database for efficient comparison.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            Set of bato_chapter_id strings
        """
        try:
            chapter_ids = db_session.query(BatoChapters.bato_chapter_id).filter(
                BatoChapters.anilist_id == anilist_id
            ).all()
            return {chapter_id[0] for chapter_id in chapter_ids}
        except Exception as e:
            logger.error(f"Error fetching existing chapter IDs for anilist_id {anilist_id}: {e}")
            db_session.rollback()
            return set()
        finally:
            db_session.remove()
    
    @staticmethod
    def bulk_insert_chapters(chapters: List[Dict]) -> int:
        """
        Efficiently insert multiple chapters with comprehensive error handling.
        
        Handles:
        - Duplicate key errors (expected for existing chapters)
        - Foreign key violations
        - Deadlocks with retry logic
        
        Requirement 5.5: Database error handling
        
        Args:
            chapters: List of chapter dictionaries
            
        Returns:
            Number of chapters successfully inserted
        """
        if not chapters:
            logger.debug("No chapters to insert")
            return 0
        
        inserted_count = 0
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                for chapter_data in chapters:
                    try:
                        # Check if chapter already exists
                        existing = db_session.query(BatoChapters).filter(
                            BatoChapters.bato_chapter_id == chapter_data['bato_chapter_id']
                        ).first()
                        
                        if not existing:
                            chapter = BatoChapters(**chapter_data)
                            db_session.add(chapter)
                            inserted_count += 1
                        else:
                            logger.debug(
                                f"Chapter {chapter_data.get('bato_chapter_id')} "
                                "already exists, skipping"
                            )
                    
                    except IntegrityError as e:
                        # Requirement 5.5: Handle duplicate key errors
                        error_msg = str(e).lower()
                        if 'duplicate' in error_msg or 'unique constraint' in error_msg:
                            logger.debug(
                                f"Duplicate chapter {chapter_data.get('bato_chapter_id')}, "
                                "skipping (expected)"
                            )
                            db_session.rollback()
                            continue
                        elif 'foreign key' in error_msg:
                            logger.error(
                                f"Foreign key violation for chapter "
                                f"{chapter_data.get('bato_chapter_id')}: {e}"
                            )
                            db_session.rollback()
                            continue
                        else:
                            raise
                    
                    except Exception as e:
                        logger.warning(
                            f"Error inserting chapter {chapter_data.get('bato_chapter_id')}: {e}"
                        )
                        db_session.rollback()
                        continue
                
                # Commit all inserts
                db_session.commit()
                logger.info(f"Successfully inserted {inserted_count} chapters")
                return inserted_count
                
            except OperationalError as e:
                # Requirement 5.5: Handle deadlocks
                error_msg = str(e).lower()
                if 'deadlock' in error_msg and attempt < max_retries:
                    import random
                    delay = random.uniform(0.1, 0.5)
                    logger.warning(
                        f"Deadlock detected in bulk_insert_chapters "
                        f"(attempt {attempt}/{max_retries}). "
                        f"Retrying in {delay:.2f}s..."
                    )
                    db_session.rollback()
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Database operational error: {e}")
                    db_session.rollback()
                    return inserted_count
            
            except Exception as e:
                logger.error(
                    f"Unexpected error bulk inserting chapters: {e}",
                    exc_info=True
                )
                db_session.rollback()
                return inserted_count
            
            finally:
                db_session.remove()
        
        return inserted_count
    
    @staticmethod
    def get_chapter_dates(anilist_id: int, limit: Optional[int] = None) -> List[datetime]:
        """
        Get publication dates for pattern analysis.
        Returns dates in descending order (newest first).
        
        Args:
            anilist_id: AniList manga ID
            limit: Optional limit on number of dates to return
            
        Returns:
            List of datetime objects
        """
        try:
            query = db_session.query(BatoChapters.date_public).filter(
                and_(
                    BatoChapters.anilist_id == anilist_id,
                    BatoChapters.date_public.isnot(None)
                )
            ).order_by(desc(BatoChapters.date_public))
            
            if limit:
                query = query.limit(limit)
            
            dates = query.all()
            return [date[0] for date in dates if date[0]]
        except Exception as e:
            logger.error(f"Error fetching chapter dates for anilist_id {anilist_id}: {e}")
            db_session.rollback()
            return []
        finally:
            db_session.remove()
    
    # ==================== Notification Methods ====================
    
    @staticmethod
    def create_notification(notification_data: Dict) -> Optional[BatoNotifications]:
        """
        Create a new notification.
        
        Args:
            notification_data: Dictionary with notification fields
            
        Returns:
            BatoNotifications object or None on error
        """
        try:
            notification = BatoNotifications(**notification_data)
            db_session.add(notification)
            db_session.commit()
            db_session.refresh(notification)
            return notification
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.remove()
    
    @staticmethod
    def get_unread_notifications(user_id: Optional[int] = None, limit: int = 50) -> List[BatoNotifications]:
        """
        Get unread notifications, sorted by importance then created_at.
        
        Args:
            user_id: Optional user ID for filtering (future use)
            limit: Maximum number of notifications to return
            
        Returns:
            List of BatoNotifications objects
        """
        try:
            query = db_session.query(BatoNotifications).filter(
                BatoNotifications.is_read == False
            ).order_by(
                desc(BatoNotifications.importance),
                desc(BatoNotifications.created_at)
            ).limit(limit)
            
            notifications = query.all()
            return notifications
        except Exception as e:
            logger.error(f"Error fetching unread notifications: {e}")
            db_session.rollback()
            return []
        finally:
            db_session.remove()
    
    @staticmethod
    def mark_notification_read(notification_id: int) -> bool:
        """
        Mark notification as read.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = db_session.query(BatoNotifications).filter(
                BatoNotifications.id == notification_id
            ).first()
            
            if notification:
                notification.is_read = True
                db_session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.remove()
    
    @staticmethod
    def get_notification_count(user_id: Optional[int] = None) -> int:
        """
        Get count of unread notifications.
        
        Args:
            user_id: Optional user ID for filtering (future use)
            
        Returns:
            Count of unread notifications
        """
        try:
            count = db_session.query(BatoNotifications).filter(
                BatoNotifications.is_read == False
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error counting unread notifications: {e}")
            db_session.rollback()
            return 0
        finally:
            db_session.remove()
    
    @staticmethod
    def get_unemitted_notifications(limit: int = 100) -> List[BatoNotifications]:
        """
        Get notifications that haven't been emitted via SocketIO yet.
        Used by the notification polling service.
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of BatoNotifications objects
        """
        try:
            query = db_session.query(BatoNotifications).filter(
                BatoNotifications.is_emitted == False
            ).order_by(
                desc(BatoNotifications.importance),
                desc(BatoNotifications.created_at)
            ).limit(limit)
            
            notifications = query.all()
            return notifications
        except Exception as e:
            logger.error(f"Error fetching unemitted notifications: {e}")
            db_session.rollback()
            return []
        finally:
            db_session.remove()
    
    @staticmethod
    def mark_notifications_emitted(notification_ids: List[int]) -> bool:
        """
        Mark multiple notifications as emitted.
        
        Args:
            notification_ids: List of notification IDs to mark as emitted
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not notification_ids:
                return True
            
            db_session.query(BatoNotifications).filter(
                BatoNotifications.id.in_(notification_ids)
            ).update(
                {BatoNotifications.is_emitted: True},
                synchronize_session=False
            )
            db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking notifications as emitted: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.remove()
    
    # ==================== Scheduling Methods ====================
    
    @staticmethod
    def get_schedule(anilist_id: int) -> Optional[BatoScrapingSchedule]:
        """
        Get scraping schedule for manga.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            BatoScrapingSchedule object or None if not found
        """
        try:
            schedule = db_session.query(BatoScrapingSchedule).filter(
                BatoScrapingSchedule.anilist_id == anilist_id
            ).first()
            return schedule
        except Exception as e:
            logger.error(f"Error fetching schedule for anilist_id {anilist_id}: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.remove()
    
    @staticmethod
    def upsert_schedule(schedule_data: Dict) -> Optional[BatoScrapingSchedule]:
        """
        Insert or update scraping schedule.
        
        Args:
            schedule_data: Dictionary with schedule fields
            
        Returns:
            BatoScrapingSchedule object or None on error
        """
        try:
            # Check if schedule exists
            existing = db_session.query(BatoScrapingSchedule).filter(
                BatoScrapingSchedule.anilist_id == schedule_data['anilist_id']
            ).first()
            
            if existing:
                # Update existing schedule
                for key, value in schedule_data.items():
                    if key != 'id' and hasattr(existing, key):
                        setattr(existing, key, value)
                db_session.commit()
                db_session.refresh(existing)
                return existing
            else:
                # Create new schedule
                schedule = BatoScrapingSchedule(**schedule_data)
                db_session.add(schedule)
                db_session.commit()
                db_session.refresh(schedule)
                return schedule
                
        except Exception as e:
            logger.error(f"Error upserting schedule: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.remove()
    
    @staticmethod
    @handle_db_connection_errors(max_retries=3)
    def get_manga_due_for_scraping(limit: Optional[int] = None) -> List[Dict]:
        """
        Get manga that need scraping now (next_scrape_at <= current time).
        Returns joined data with manga details.
        
        Args:
            limit: Optional limit on number of manga to return
            
        Returns:
            List of dictionaries with schedule and manga info
        """
        try:
            current_time = datetime.now()
            
            query = db_session.query(
                BatoScrapingSchedule,
                BatoMangaDetails
            ).join(
                BatoMangaDetails,
                BatoScrapingSchedule.anilist_id == BatoMangaDetails.anilist_id
            ).filter(
                and_(
                    BatoScrapingSchedule.next_scrape_at <= current_time,
                    BatoScrapingSchedule.is_active == True
                )
            ).order_by(
                desc(BatoScrapingSchedule.priority),
                BatoScrapingSchedule.next_scrape_at
            )
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            # Convert to list of dictionaries
            manga_list = []
            for schedule, details in results:
                manga_list.append({
                    'anilist_id': schedule.anilist_id,
                    'bato_link': schedule.bato_link,
                    'bato_id': details.bato_id,
                    'manga_name': details.name,
                    'scraping_interval_hours': schedule.scraping_interval_hours,
                    'last_scraped_at': schedule.last_scraped_at,
                    'priority': schedule.priority,
                    'upload_status': details.upload_status
                })
            
            return manga_list
            
        except Exception as e:
            logger.error(f"Error fetching manga due for scraping: {e}")
            db_session.rollback()
            return []
        finally:
            db_session.remove()
    
    @staticmethod
    @handle_db_connection_errors(max_retries=3)
    def update_schedule_after_scrape(anilist_id: int, next_scrape_at: datetime, 
                                     new_chapters_found: int = 0) -> bool:
        """
        Update schedule after a scraping job completes.
        
        Args:
            anilist_id: AniList manga ID
            next_scrape_at: When to scrape next
            new_chapters_found: Number of new chapters found
            
        Returns:
            True if successful, False otherwise
        """
        try:
            schedule = db_session.query(BatoScrapingSchedule).filter(
                BatoScrapingSchedule.anilist_id == anilist_id
            ).first()
            
            if schedule:
                schedule.last_scraped_at = datetime.now()
                schedule.next_scrape_at = next_scrape_at
                
                if new_chapters_found > 0:
                    schedule.consecutive_no_update_count = 0
                    schedule.total_chapters_tracked += new_chapters_found
                else:
                    schedule.consecutive_no_update_count += 1
                
                db_session.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating schedule after scrape for anilist_id {anilist_id}: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.remove()
    
    # ==================== Logging Methods ====================
    
    @staticmethod
    @handle_db_connection_errors(max_retries=3)
    def log_scraping_job(log_data: Dict) -> Optional[BatoScraperLog]:
        """
        Log scraping job results for monitoring.
        
        Args:
            log_data: Dictionary with log fields
            
        Returns:
            BatoScraperLog object or None on error
        """
        try:
            log_entry = BatoScraperLog(**log_data)
            db_session.add(log_entry)
            db_session.commit()
            db_session.refresh(log_entry)
            return log_entry
        except Exception as e:
            logger.error(f"Error logging scraping job: {e}")
            db_session.rollback()
            return None
        finally:
            db_session.remove()
    
    @staticmethod
    def get_scraping_stats(hours: int = 24) -> Dict:
        """
        Get scraping statistics for monitoring dashboard.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            logs = db_session.query(BatoScraperLog).filter(
                BatoScraperLog.scraped_at >= cutoff_time
            ).all()
            
            if not logs:
                return {
                    'total_jobs': 0,
                    'successful_jobs': 0,
                    'failed_jobs': 0,
                    'success_rate': 0.0,
                    'average_duration': 0.0,
                    'total_chapters_found': 0,
                    'total_new_chapters': 0
                }
            
            total_jobs = len(logs)
            successful_jobs = sum(1 for log in logs if log.status == 'success')
            failed_jobs = sum(1 for log in logs if log.status == 'failed')
            
            durations = [log.duration_seconds for log in logs if log.duration_seconds]
            average_duration = sum(durations) / len(durations) if durations else 0.0
            
            total_chapters_found = sum(log.chapters_found for log in logs)
            total_new_chapters = sum(log.new_chapters for log in logs)
            
            return {
                'total_jobs': total_jobs,
                'successful_jobs': successful_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0.0,
                'average_duration': round(average_duration, 2),
                'total_chapters_found': total_chapters_found,
                'total_new_chapters': total_new_chapters,
                'error_rate': (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error fetching scraping stats: {e}")
            db_session.rollback()
            return {}
        finally:
            db_session.remove()
    
    @staticmethod
    def get_recent_logs(limit: int = 20) -> List[BatoScraperLog]:
        """
        Get recent scraping logs for monitoring.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of BatoScraperLog objects
        """
        try:
            logs = db_session.query(BatoScraperLog).order_by(
                desc(BatoScraperLog.scraped_at)
            ).limit(limit).all()
            return logs
        except Exception as e:
            logger.error(f"Error fetching recent logs: {e}")
            db_session.rollback()
            return []
        finally:
            db_session.remove()
