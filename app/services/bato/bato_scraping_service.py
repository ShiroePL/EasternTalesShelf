"""
BatoScrapingService - Background Service for Bato.to Chapter Scraping

Manages automated scraping of manga chapters from Bato.to based on intelligent schedules.
Runs as a background thread with concurrent job execution and retry logic.

Requirements:
- 5.1: Initialize background scraping service on app startup
- 5.2: Query manga with next_scrape_at <= current time
- 5.3: Log start time and scrape_type to bato_scraper_log
- 5.4: Update last_scraped_at and calculate next_scrape_at on completion
- 5.5: Retry failed jobs with exponential backoff (max 3 attempts)
- 5.6: Limit concurrent jobs to 5 to avoid rate limiting
- 10.1: Record duration_seconds in bato_scraper_log
- 10.2: Record chapters_found and new_chapters counts
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import traceback

from app.database_module.bato_repository import BatoRepository
from app.services.bato.chapter_comparator import ChapterComparator
from app.services.bato.notification_manager import NotificationManager
from app.services.bato.scheduling_engine import SchedulingEngine
from app.services.bato.error_handler import (
    ErrorHandler,
    NetworkError,
    GraphQLError,
    RateLimitError,
    DatabaseError,
    with_retry,
    log_performance
)
from app.scraper.bato_graphql_hidden_api.bato_chapters_list_graphql import BatoChaptersListGraphQL
from app.scraper.bato_graphql_hidden_api.bato_manga_details_graphql import BatoMangaDetailsGraphQL

logger = logging.getLogger(__name__)


class BatoScrapingService:
    """
    Background service that manages scraping jobs for Bato manga.
    
    This service:
    - Runs as a daemon thread
    - Checks for manga due for scraping every 5 minutes
    - Executes up to 5 concurrent scraping jobs
    - Implements retry logic with exponential backoff
    - Updates schedules and creates notifications
    - Logs all operations for monitoring
    """
    
    # Service configuration
    CHECK_INTERVAL_SECONDS = 300  # Check every 5 minutes
    MAX_CONCURRENT_JOBS = 5  # Requirement 5.6
    MAX_RETRY_ATTEMPTS = 3  # Requirement 5.5
    INITIAL_RETRY_DELAY = 1  # seconds
    MAX_RETRY_DELAY = 60  # seconds
    
    def __init__(self):
        """Initialize the BatoScrapingService with all dependencies."""
        self.running = False
        self.thread = None
        self.executor = ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_JOBS)
        
        # Initialize dependencies
        self.repository = BatoRepository()
        self.chapter_comparator = ChapterComparator()
        self.notification_manager = NotificationManager()
        self.scheduling_engine = SchedulingEngine()
        
        # Initialize scrapers
        self.chapters_scraper = BatoChaptersListGraphQL(verbose=False)
        self.details_scraper = BatoMangaDetailsGraphQL(verbose=False)
        
        logger.info("BatoScrapingService initialized")
    
    def start(self):
        """
        Start the background service.
        
        Requirement 5.1: Initialize background scraping service
        """
        if self.running:
            logger.warning("BatoScrapingService is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        
        logger.info("BatoScrapingService started successfully")
    
    def stop(self):
        """
        Stop the background service gracefully.
        
        Waits for current jobs to complete before shutting down.
        """
        if not self.running:
            logger.warning("BatoScrapingService is not running")
            return
        
        logger.info("Stopping BatoScrapingService...")
        self.running = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=30)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("BatoScrapingService stopped successfully")
    
    def run_loop(self):
        """
        Main service loop - runs every 5 minutes.
        
        This is the core of the background service that:
        1. Queries manga due for scraping
        2. Creates scraping jobs
        3. Executes jobs concurrently
        4. Processes results
        5. Updates schedules
        """
        logger.info("BatoScrapingService main loop started")
        
        while self.running:
            try:
                logger.info("Starting scraping cycle...")
                
                # Requirement 5.2: Query manga due for scraping
                manga_list = self.get_manga_due_for_scraping()
                
                if not manga_list:
                    logger.info("No manga due for scraping at this time")
                else:
                    logger.info(f"Found {len(manga_list)} manga due for scraping")
                    
                    # Execute scraping jobs concurrently
                    self._execute_concurrent_jobs(manga_list)
                
                # Wait for next check interval
                logger.info(f"Scraping cycle complete. Sleeping for {self.CHECK_INTERVAL_SECONDS} seconds...")
                
                # Sleep in small increments to allow for graceful shutdown
                for _ in range(self.CHECK_INTERVAL_SECONDS):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.error(traceback.format_exc())
                # Sleep before retrying
                time.sleep(60)
        
        logger.info("BatoScrapingService main loop exited")
    
    def get_manga_due_for_scraping(self) -> List[Dict]:
        """
        Query manga where next_scrape_at <= now.
        
        Requirement 5.2: Query all manga entries with next_scrape_at less than current time
        
        Returns:
            List of manga dictionaries with schedule and details
        """
        try:
            manga_list = self.repository.get_manga_due_for_scraping()
            
            if manga_list:
                logger.info(f"Retrieved {len(manga_list)} manga due for scraping:")
                for manga in manga_list[:5]:  # Log first 5
                    logger.info(
                        f"  - {manga['manga_name']} (ID: {manga['anilist_id']}, "
                        f"Priority: {manga['priority']})"
                    )
                if len(manga_list) > 5:
                    logger.info(f"  ... and {len(manga_list) - 5} more")
            
            return manga_list
            
        except Exception as e:
            logger.error(f"Error getting manga due for scraping: {e}")
            return []
    
    def _execute_concurrent_jobs(self, manga_list: List[Dict]):
        """
        Execute scraping jobs concurrently with max workers limit.
        
        Requirement 5.6: Limit concurrent jobs to 5
        
        Args:
            manga_list: List of manga to scrape
        """
        futures = {}
        
        # Submit all jobs to executor
        for manga_data in manga_list:
            future = self.executor.submit(self.execute_scraping_job, manga_data)
            futures[future] = manga_data
        
        # Process completed jobs
        completed = 0
        failed = 0
        
        for future in as_completed(futures):
            manga_data = futures[future]
            try:
                success = future.result()
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(
                    f"Job failed for {manga_data['manga_name']} "
                    f"(ID: {manga_data['anilist_id']}): {e}"
                )
                failed += 1
        
        logger.info(
            f"Concurrent job execution complete: "
            f"{completed} successful, {failed} failed"
        )
    
    def execute_scraping_job(self, manga_data: Dict) -> bool:
        """
        Execute a single scraping job with comprehensive error handling.
        
        Requirements:
        - 5.3: Log start time and scrape_type
        - 5.5: Retry with exponential backoff (max 3 attempts)
        - 5.5: Network error retry logic
        - 5.5: Rate limiting detection (429 responses) with 5-minute pause
        
        Args:
            manga_data: Dictionary with manga info (anilist_id, bato_id, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        anilist_id = manga_data['anilist_id']
        bato_id = manga_data['bato_id']
        manga_name = manga_data['manga_name']
        
        # Requirement 5.5: Check rate limit before starting
        if ErrorHandler.is_rate_limited():
            rate_info = ErrorHandler.get_rate_limit_info()
            logger.warning(
                f"Skipping {manga_name} due to rate limit. "
                f"Remaining: {rate_info['remaining_seconds']}s"
            )
            return False
        
        logger.info(f"Starting scraping job for {manga_name} (ID: {anilist_id})")
        
        # Requirement 5.3: Log start time
        start_time = datetime.now()
        last_error = None
        
        # Requirement 5.5: Try with exponential backoff
        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                logger.info(
                    f"Scraping attempt {attempt}/{self.MAX_RETRY_ATTEMPTS} "
                    f"for {manga_name}"
                )
                
                # Scrape chapters and details with error handling
                try:
                    chapters_data = self.chapters_scraper.scrape_chapters(
                        bato_id, 
                        get_manga_title=False
                    )
                except Exception as e:
                    # Requirement 5.5: Handle network and GraphQL errors
                    if '429' in str(e) or 'rate limit' in str(e).lower():
                        ErrorHandler.set_rate_limit(300)  # 5 minutes
                        raise RateLimitError(f"Rate limited while scraping chapters: {e}")
                    raise NetworkError(f"Failed to scrape chapters: {e}")
                
                try:
                    details_data = self.details_scraper.scrape_manga_details(bato_id)
                except Exception as e:
                    # Requirement 5.5: Handle network and GraphQL errors
                    if '429' in str(e) or 'rate limit' in str(e).lower():
                        ErrorHandler.set_rate_limit(300)  # 5 minutes
                        raise RateLimitError(f"Rate limited while scraping details: {e}")
                    raise NetworkError(f"Failed to scrape details: {e}")
                
                # Calculate duration
                duration_seconds = (datetime.now() - start_time).total_seconds()
                
                # Requirement 10.5: Log warning if operation is slow
                if duration_seconds > 2.0:
                    logger.warning(
                        f"Scraping took {duration_seconds:.2f}s for {manga_name} "
                        "(exceeds 2s threshold)"
                    )
                
                # Process results with database error handling
                success = self.process_scraping_results(
                    manga_data, 
                    chapters_data, 
                    details_data,
                    duration_seconds
                )
                
                if success:
                    logger.info(
                        f"Successfully scraped {manga_name} "
                        f"in {duration_seconds:.2f}s"
                    )
                    return True
                else:
                    logger.warning(f"Failed to process results for {manga_name}")
                    last_error = "Failed to process results"
                    
            except RateLimitError as e:
                # Requirement 5.5: Don't retry on rate limit
                logger.error(
                    f"Rate limited while scraping {manga_name}: {e}. "
                    "Aborting job."
                )
                duration_seconds = (datetime.now() - start_time).total_seconds()
                self._log_scraping_failure(
                    manga_data,
                    f"Rate limited: {str(e)}",
                    duration_seconds
                )
                return False
                
            except (NetworkError, GraphQLError) as e:
                # Requirement 5.5: Retry network and GraphQL errors
                last_error = str(e)
                logger.error(
                    f"Scraping attempt {attempt} failed for {manga_name}: {e}"
                )
                
                if attempt < self.MAX_RETRY_ATTEMPTS:
                    # Requirement 5.5: Exponential backoff
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1)),
                        self.MAX_RETRY_DELAY
                    )
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    
            except Exception as e:
                # Unexpected errors
                last_error = str(e)
                logger.error(
                    f"Unexpected error in attempt {attempt} for {manga_name}: {e}",
                    exc_info=True
                )
                
                if attempt < self.MAX_RETRY_ATTEMPTS:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1)),
                        self.MAX_RETRY_DELAY
                    )
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries exhausted
        logger.error(
            f"All {self.MAX_RETRY_ATTEMPTS} attempts failed for {manga_name}"
        )
        
        # Log final failure
        duration_seconds = (datetime.now() - start_time).total_seconds()
        self._log_scraping_failure(
            manga_data,
            last_error or "Unknown error",
            duration_seconds
        )
        
        return False
    
    def process_scraping_results(self, manga_data: Dict, 
                                 chapters_data: Dict, 
                                 details_data: Dict,
                                 duration_seconds: float) -> bool:
        """
        Process scraping results and update database.
        
        This method:
        1. Updates manga details
        2. Finds new chapters
        3. Inserts new chapters
        4. Creates notifications
        5. Updates schedule
        6. Logs the job
        
        Requirements:
        - 5.4: Update last_scraped_at and calculate next_scrape_at
        - 10.1: Record duration_seconds
        - 10.2: Record chapters_found and new_chapters counts
        
        Args:
            manga_data: Original manga data
            chapters_data: Scraped chapters from API
            details_data: Scraped manga details from API
            duration_seconds: Time taken to scrape
            
        Returns:
            True if successful, False otherwise
        """
        anilist_id = manga_data['anilist_id']
        bato_link = manga_data['bato_link']
        manga_name = manga_data['manga_name']
        
        try:
            # 1. Update manga details
            old_status = None
            manga_details = self.repository.get_manga_details(anilist_id)
            if manga_details:
                old_status = manga_details.upload_status
            
            details_to_save = {
                'anilist_id': anilist_id,
                'bato_link': bato_link,
                'bato_id': details_data['bato_id'],
                'name': details_data['name'],
                'alt_names': ','.join(details_data.get('alt_names', [])),
                'authors': ','.join(details_data.get('authors', [])),
                'artists': ','.join(details_data.get('artists', [])),
                'genres': ','.join(details_data.get('genres', [])),
                'orig_lang': details_data.get('orig_lang', ''),
                'original_status': details_data.get('original_status', ''),
                'upload_status': details_data.get('upload_status', ''),
                'summary': details_data.get('summary', ''),
                'stat_score_val': details_data.get('stat_score_val'),
                'stat_count_votes': details_data.get('stat_count_votes', 0),
                'stat_count_follows': details_data.get('stat_count_follows', 0)
            }
            
            self.repository.upsert_manga_details(details_to_save)
            
            # Check for status change
            new_status = details_data.get('upload_status')
            if old_status and new_status and old_status != new_status:
                logger.info(
                    f"Status change detected for {manga_name}: "
                    f"{old_status} -> {new_status}"
                )
                self.notification_manager.create_status_change_notification(
                    {
                        'anilist_id': anilist_id,
                        'bato_link': bato_link,
                        'manga_name': manga_name
                    },
                    old_status,
                    new_status
                )
            
            # 2. Find new chapters
            scraped_chapters = chapters_data.get('chapters', [])
            chapters_found = len(scraped_chapters)
            
            new_chapters = self.chapter_comparator.find_new_chapters(
                anilist_id, 
                scraped_chapters
            )
            new_chapters_count = len(new_chapters)
            
            logger.info(
                f"Found {new_chapters_count} new chapters out of "
                f"{chapters_found} total for {manga_name}"
            )
            
            # 3. Insert new chapters
            if new_chapters:
                chapters_to_insert = []
                for chapter in new_chapters:
                    chapter_data = {
                        'anilist_id': anilist_id,
                        'bato_link': bato_link,
                        'bato_chapter_id': chapter['bato_chapter_id'],
                        'chapter_number': chapter['chapter_number'],
                        'dname': chapter['dname'],
                        'title': chapter.get('title'),
                        'url_path': chapter['url_path'],
                        'full_url': chapter['full_url'],
                        'date_create': chapter.get('date_create'),
                        'date_public': chapter.get('date_public'),
                        'stat_count_views_guest': chapter.get('stat_count_views_guest', 0),
                        'stat_count_views_login': chapter.get('stat_count_views_login', 0),
                        'stat_count_views_total': chapter.get('stat_count_views_total', 0),
                        'stat_count_post_reply': chapter.get('stat_count_post_reply', 0)
                    }
                    chapters_to_insert.append(chapter_data)
                
                inserted_count = self.repository.bulk_insert_chapters(chapters_to_insert)
                logger.info(f"Inserted {inserted_count} new chapters for {manga_name}")
                
                # 4. Create notifications
                self._create_chapter_notifications(
                    manga_data, 
                    new_chapters, 
                    chapters_to_insert
                )
            
            # 5. Update schedule (Requirement 5.4)
            self.scheduling_engine.update_schedule_after_scrape(
                anilist_id,
                new_chapters_count
            )
            
            # 6. Log the job (Requirements 10.1, 10.2)
            self._log_scraping_success(
                manga_data,
                chapters_found,
                new_chapters_count,
                duration_seconds
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing scraping results for {manga_name}: {e}")
            logger.error(traceback.format_exc())
            
            # Log the failure
            self._log_scraping_failure(manga_data, str(e), duration_seconds)
            return False
    
    def _create_chapter_notifications(self, manga_data: Dict, 
                                     new_chapters: List[Dict],
                                     chapters_to_insert: List[Dict]):
        """
        Create notifications for new chapters.
        
        Determines whether to create individual or batch notifications
        based on the number of new chapters.
        
        Args:
            manga_data: Manga information
            new_chapters: List of new chapter data from scraper
            chapters_to_insert: List of chapter data prepared for database
        """
        manga_name = manga_data['manga_name']
        
        # Check if batch notification should be created
        should_batch = self.chapter_comparator.should_create_batch_notification(
            new_chapters
        )
        
        if should_batch:
            # Create batch notification
            logger.info(
                f"Creating batch notification for {len(new_chapters)} "
                f"chapters of {manga_name}"
            )
            
            # Prepare chapter info for notification
            chapters_info = []
            for i, chapter in enumerate(new_chapters):
                chapters_info.append({
                    'chapter_dname': chapter['dname'],
                    'chapter_full_url': chapter['full_url']
                })
            
            self.notification_manager.create_batch_notification(
                {
                    'anilist_id': manga_data['anilist_id'],
                    'bato_link': manga_data['bato_link'],
                    'manga_name': manga_name
                },
                chapters_info
            )
        else:
            # Create individual notifications
            logger.info(
                f"Creating {len(new_chapters)} individual notifications "
                f"for {manga_name}"
            )
            
            for chapter in new_chapters:
                self.notification_manager.create_new_chapter_notification({
                    'anilist_id': manga_data['anilist_id'],
                    'bato_link': manga_data['bato_link'],
                    'manga_name': manga_name,
                    'chapter_dname': chapter['dname'],
                    'chapter_full_url': chapter['full_url']
                })
    
    def _log_scraping_success(self, manga_data: Dict, 
                             chapters_found: int,
                             new_chapters: int,
                             duration_seconds: float):
        """
        Log successful scraping job.
        
        Requirements:
        - 5.3: Log to bato_scraper_log
        - 10.1: Record duration_seconds
        - 10.2: Record chapters_found and new_chapters
        
        Args:
            manga_data: Manga information
            chapters_found: Total chapters scraped
            new_chapters: Number of new chapters detected
            duration_seconds: Time taken to scrape
        """
        try:
            log_data = {
                'anilist_id': manga_data['anilist_id'],
                'bato_link': manga_data['bato_link'],
                'scrape_type': 'scheduled',
                'status': 'success',
                'chapters_found': chapters_found,
                'new_chapters': new_chapters,
                'duration_seconds': round(duration_seconds, 2),
                'scraped_at': datetime.now()
            }
            
            self.repository.log_scraping_job(log_data)
            
        except Exception as e:
            logger.error(f"Error logging scraping success: {e}")
    
    def _log_scraping_failure(self, manga_data: Dict, 
                             error_message: str,
                             duration_seconds: float):
        """
        Log failed scraping job.
        
        Requirement 5.3: Log to bato_scraper_log
        
        Args:
            manga_data: Manga information
            error_message: Error description
            duration_seconds: Time taken before failure
        """
        try:
            log_data = {
                'anilist_id': manga_data['anilist_id'],
                'bato_link': manga_data['bato_link'],
                'scrape_type': 'scheduled',
                'status': 'failed',
                'chapters_found': 0,
                'new_chapters': 0,
                'duration_seconds': round(duration_seconds, 2),
                'error_message': error_message[:500],  # Truncate long errors
                'scraped_at': datetime.now()
            }
            
            self.repository.log_scraping_job(log_data)
            
        except Exception as e:
            logger.error(f"Error logging scraping failure: {e}")
    
    def get_service_status(self) -> Dict:
        """
        Get current service status for monitoring.
        
        Includes rate limit information for debugging.
        
        Returns:
            Dictionary with service status information
        """
        rate_limit_info = ErrorHandler.get_rate_limit_info()
        
        return {
            'running': self.running,
            'thread_alive': self.thread.is_alive() if self.thread else False,
            'max_workers': self.MAX_CONCURRENT_JOBS,
            'check_interval_seconds': self.CHECK_INTERVAL_SECONDS,
            'max_retry_attempts': self.MAX_RETRY_ATTEMPTS,
            'rate_limit': rate_limit_info
        }


# Global service instance
_service_instance: Optional[BatoScrapingService] = None


def get_service_instance() -> BatoScrapingService:
    """
    Get or create the global service instance.
    
    Returns:
        BatoScrapingService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = BatoScrapingService()
    return _service_instance


def start_service():
    """Start the global service instance."""
    service = get_service_instance()
    service.start()


def stop_service():
    """Stop the global service instance."""
    global _service_instance
    if _service_instance:
        _service_instance.stop()
        _service_instance = None
