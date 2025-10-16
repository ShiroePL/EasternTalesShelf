import logging
import os
import random
import time
import json
from datetime import datetime
import schedule
from app.functions.sqlalchemy_fns import save_manga_details
from app.functions.class_mangalist import db_session, MangaStatusNotification
from sqlalchemy import text, create_engine
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for
from app.functions.manga_updates_spider import MangaUpdatesSpider
from dataclasses import dataclass
from typing import List, Optional
from app.functions.vector_db_stuff.ai_related.groq_api import send_to_groq
import asyncio
import re
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URI

# Initialize crochet for Scrapy to work with async code
setup()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MangaStatusUpdate:
    anilist_id: int
    title: str  # We'll need to add title to our query
    old_status: Optional[str]
    new_status: Optional[str]
    timestamp: datetime
    url: str

STATUS_ANALYSIS_PROMPT = """You are a manhwa status analyzer. Analyze the following status changes and identify significant events.
Focus on these types of changes:
1. Season endings or beginnings
2. Series completion
3. New side stories or extras
4. Hiatus announcements
5. Licensing status changes

For each manga, determine if there are important changes that readers should know about.
IMPORTANT: Return ONLY a JSON object without any additional text or explanation. The response must be a valid JSON in this format:
{
  "notifications": [
    {
      "title": "manga_title",
      "id": manga_id,  // Include the provided manga ID in your response
      "type": "notification_type",  // one of: season_end, series_end, side_story, hiatus, license
      "message": "human readable message about the change",
      "importance": 1-3  // 1: low, 2: medium, 3: high
    }
  ]
}

Only include manga where significant changes occurred.
If there are no significant changes (so nothing changed), don't mention it.
Compare the statuses carefully - look for changes in chapter counts, season completions, or status changes.
If there are few notification for one manhwa, glue them to one notificiation.
Example of significant change: "S4: 36 Chapters (116~)" to "S4: 40 Chapters (116~155)" indicates season 4 completion.

Here are the status changes to analyze:

"""

NOTIFICATION_FILTER_PROMPT = """You are a notification filter. Your job is to filter out notifications that do NOT represent truly significant or NEW information.

FILTER OUT notifications that:
- Say "no significant changes detected"
- Mention "series is still ongoing" without new developments
- State "remains on hiatus" without new information
- Say "no new chapters or updates" 
- Indicate "chapter count remains the same" or similar
- Are redundant or repetitive about the same status

KEEP notifications that:
- Announce new seasons starting
- Announce series completion or ending
- Announce new hiatus (first time)
- Announce return from hiatus
- Announce significant chapter milestones
- Announce licensing changes
- Announce side stories starting

Return ONLY a JSON object without any additional text:
{
  "filtered_notifications": [
    {
      "title": "manga_title",
      "id": manga_id,
      "type": "notification_type",
      "message": "human readable message about the change",
      "importance": 1-3
    }
  ]
}

Here are the notifications to filter:

"""

class MangaUpdatesUpdateService:
    def __init__(self):
        self.delay_between_requests = random.uniform(4.0, 7.0)  # random delay between 4.0-7.0 seconds with decimal precision
        self.status_updates: List[MangaStatusUpdate] = []
        self.batch_size = 2
        self.engine = create_engine(DATABASE_URI, pool_recycle=3600, pool_pre_ping=True)
        self.setup_service_logging()
    
    def setup_service_logging(self):
        """
        Setup dedicated logging for the manga updates service.
        Creates folder 'logs' next to mangaupdates_update_service.py
        """
        # katalog, w którym znajduje się bieżący plik
        current_dir = os.path.dirname(__file__)

        # ścieżka do folderu logs: .../app/services/logs
        log_dir = os.path.join(current_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir, f"mangaupdates_service_{datetime.now():%Y-%m-%d}.log"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.info("MangaUpdatesUpdateService initialized with enhanced logging")

    
    def log_service_operation(self, operation, data, status="success"):
        """Log service operations in structured format"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "status": status,
            "data": data
        }
        
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        log_file = os.path.join(log_dir, f"mangaupdates_operations_{datetime.now().strftime('%Y-%m-%d')}.log")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + '\n' + '-'*50 + '\n')

    @wait_for(timeout=30.0)
    def run_spider(self, url, anilist_id):
        """Run the MangaUpdates spider for a given URL"""
        runner = CrawlerRunner()
        results = {}
        deferred = runner.crawl(
            MangaUpdatesSpider, 
            start_url=url, 
            anilist_id=anilist_id, 
            results=results
        )
        # Wait for spider to complete and return results
        deferred.addCallback(lambda _: results.get('status'))
        deferred.addErrback(lambda failure: logger.error(f"Spider failed: {failure}"))
        return deferred

    def get_current_status(self, anilist_id):
        """Get the current status from mangaupdates_details table"""
        try:
            query = text("""
                SELECT status
                FROM mangaupdates_details
                WHERE anilist_id = :anilist_id
            """)
            result = db_session.execute(query, {"anilist_id": anilist_id}).first()
            return result.status if result else None
        except Exception as e:
            logger.error(f"Error fetching current status: {e}")
            return None

    def get_manga_with_updates_links(self):
        """Fetch all manga entries that have MangaUpdates links"""
        try:
            # First, get total counts for diagnostics
            diagnostic_query = text("""
                SELECT 
                    COUNT(*) as total_manga,
                    SUM(CASE WHEN ml.external_links IS NOT NULL AND ml.external_links != '' THEN 1 ELSE 0 END) as has_links,
                    SUM(CASE WHEN ml.external_links LIKE '%mangaupdates.com%' THEN 1 ELSE 0 END) as has_mu_links
                FROM manga_list ml
            """)
            diag_result = db_session.execute(diagnostic_query).first()
            logger.info(f"=== MANGA DATABASE DIAGNOSTICS ===")
            logger.info(f"Total manga in database: {diag_result.total_manga}")
            logger.info(f"Manga with external_links: {diag_result.has_links}")
            logger.info(f"Manga with MangaUpdates links: {diag_result.has_mu_links}")
            logger.info(f"===================================")
            
            # Main query to get manga with MangaUpdates links
            query = text("""
                SELECT ml.id_anilist, ml.external_links, mu.licensed, mu.completed,
                       mu.status as old_status,
                       ml.title_english
                FROM manga_list ml  -- Always use production table
                LEFT JOIN mangaupdates_details mu ON ml.id_anilist = mu.anilist_id
                WHERE ml.external_links LIKE '%mangaupdates.com%'
                ORDER BY ml.id_anilist
            """)
            
            result = db_session.execute(query)
            manga_list = [(row.id_anilist, row.external_links, row.licensed, row.completed,
                     row.old_status, row.title_english) 
                    for row in result]
            
            # Log the IDs being processed for verification
            logger.info(f"Found {len(manga_list)} manga with MangaUpdates links")
            logger.info(f"First 10 manga IDs: {[m[0] for m in manga_list[:10]]}")
            logger.info(f"Last 10 manga IDs: {[m[0] for m in manga_list[-10:]]}")
            
            return manga_list
        except Exception as e:
            logger.error(f"Error fetching manga with updates links: {e}")
            logger.exception("Full exception:")
            return []

    def extract_mangaupdates_url(self, external_links):
        """Extract MangaUpdates URL from external links JSON string"""
        try:
            import json
            links = json.loads(external_links)
            for link in links:
                if 'mangaupdates.com' in link:
                    return link
        except Exception as e:
            logger.error(f"Error extracting MangaUpdates URL: {e}")
        return None

    def should_update_manga(self, licensed, completed):
        """Determine if manga needs updating based on its status"""
        # Skip if both licensed and completed
        if licensed and completed:  # Now checks for boolean True/1 values
            return False
        return True

    def save_notification(self, notification_data: dict, manga_update: MangaStatusUpdate):
        """Save a notification to the database"""
        session = None
        logger.info(f"Starting save_notification for {manga_update.title}")
        try:
            # Create a new session for this operation
            Session = sessionmaker(bind=self.engine)
            session = Session()
            logger.info(f"Created new session for {manga_update.title}")

            # Check if notification already exists
            existing = session.query(MangaStatusNotification).filter(
                MangaStatusNotification.anilist_id == manga_update.anilist_id,
                MangaStatusNotification.notification_type == notification_data['type'],
                MangaStatusNotification.message == notification_data['message']
            ).first()

            if existing:
                logger.info(f"Notification already exists for manga {manga_update.title}")
                return

            logger.info(f"Creating notification object for {manga_update.title}")
            notification = MangaStatusNotification(
                anilist_id=manga_update.anilist_id,
                title=manga_update.title,
                notification_type=notification_data['type'],
                message=notification_data['message'],
                old_status=manga_update.old_status,
                new_status=manga_update.new_status,
                importance=notification_data['importance'],
                url=manga_update.url
            )
            
            logger.info(f"Adding notification to session for {manga_update.title}")
            session.add(notification)
            
            logger.info(f"Committing notification for {manga_update.title}")
            session.commit()
            logger.info(f"Successfully saved notification for manga {manga_update.title}")
            
            # Log the notification save
            self.log_service_operation(
                "notification_saved",
                {
                    "anilist_id": manga_update.anilist_id,
                    "title": manga_update.title,
                    "notification_type": notification_data['type'],
                    "message": notification_data['message'],
                    "importance": notification_data['importance']
                }
            )

        except Exception as e:
            logger.error(f"Error saving notification for {manga_update.title}: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full error details: {str(e)}")
            if session:
                logger.info(f"Rolling back session for {manga_update.title}")
                session.rollback()
            # If it's a connection error, try to reconnect
            if "MySQL server has gone away" in str(e):
                try:
                    self.engine.dispose()
                    self.engine = create_engine(DATABASE_URI, pool_recycle=3600, pool_pre_ping=True)
                    logger.info("Reconnected to database after connection loss")
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect to database: {reconnect_error}")
        finally:
            if session:
                try:
                    logger.info(f"Closing session for {manga_update.title}")
                    session.close()
                    logger.info(f"Successfully closed session for {manga_update.title}")
                except Exception as close_error:
                    logger.error(f"Error closing session for {manga_update.title}: {close_error}")

    async def filter_notifications(self, notifications_to_filter):
        """Filter out non-significant notifications using AI"""
        if not notifications_to_filter:
            logger.info("No notifications to filter")
            return []

        logger.info(f"Filtering {len(notifications_to_filter)} notifications")
        
        # Format the notifications for filtering
        prompt = NOTIFICATION_FILTER_PROMPT
        for notification in notifications_to_filter:
            prompt += f"Title: {notification['title']} (ID: {notification.get('id', 'N/A')})\n"
            prompt += f"Type: {notification['type']}\n"
            prompt += f"Message: {notification['message']}\n"
            prompt += f"Importance: {notification['importance']}\n\n"

        logger.info("Complete filter prompt being sent to Groq:")
        logger.info("=" * 50)
        logger.info(prompt)
        logger.info("=" * 50)

        try:
            # Call Groq API for filtering with reasoning
            response, _, _, _ = send_to_groq([{"role": "user", "content": prompt}])
            
            logger.info(f"Received filter response from Groq: {response}")
            
            # Clean the response - take only the JSON part
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
                logger.info(f"Extracted filter JSON: {json_str}")
            else:
                logger.error("No JSON found in filter response")
                return []
            
            # Parse the response as JSON
            import json
            filter_result = json.loads(json_str)
            
            filtered_notifications = filter_result.get('filtered_notifications', [])
            logger.info(f"Filter result: {len(notifications_to_filter)} -> {len(filtered_notifications)} notifications")
            
            return filtered_notifications
            
        except Exception as e:
            logger.error(f"Error filtering notifications: {e}")
            logger.error(f"Full filter response was: {response}")
            # Return original notifications if filtering fails
            return notifications_to_filter

    async def analyze_status_changes(self):
        """Analyze status changes using LLM in batches of 3 with additional filtering"""
        if len(self.status_updates) < 1:
            logger.info("No updates for analysis")
            return

        logger.info("Starting status change analysis with two-step filtering")
        
        # Log the start of analysis
        self.log_service_operation(
            "analysis_started",
            {
                "total_updates": len(self.status_updates),
                "model": "meta-llama/llama-4-maverick-17b-128e-instruct"
            }
        )
        
        # Process updates in batches of 3
        batch_size = 3
        total_updates = len(self.status_updates)
        all_potential_notifications = []
        
        for i in range(0, total_updates, batch_size):
            batch = self.status_updates[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(total_updates + batch_size - 1)//batch_size}")

            # Format the prompt for the current batch
            prompt = STATUS_ANALYSIS_PROMPT
            for update in batch:
                prompt += f"Manga: {update.title} (ID: {update.anilist_id})\n"
                prompt += f"Old status: {update.old_status}\n"
                prompt += f"New status: {update.new_status}\n\n"

            logger.info("Complete prompt being sent to Groq:")
            logger.info("=" * 50)
            logger.info(prompt)
            logger.info("=" * 50)

            logger.info("Sending request to Groq API")
            try:
                # Call Groq API for initial analysis with reasoning
                response, _, _, _ = send_to_groq([{"role": "user", "content": prompt}])
                
                logger.info(f"Received response from Groq: {response}")
                
                # Clean the response - take only the JSON part
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    logger.info(f"Extracted JSON: {json_str}")
                else:
                    logger.error("No JSON found in response")
                    continue
                
                # Parse the response as JSON
                import json
                analysis = json.loads(json_str)
                
                # Collect potential notifications from this batch
                batch_notifications = []
                for notification in analysis.get('notifications', []):
                    logger.info(f"Processing potential notification: {notification}")
                    manga_update = None
                    
                    # Try to find by ID first (most reliable)
                    if 'id' in notification:
                        manga_update = next(
                            (update for update in batch 
                             if update.anilist_id == notification['id']),
                            None
                        )
                        if manga_update:
                            logger.info(f"Found manga update by ID {notification['id']}")

                    # If ID matching failed, try title matching as fallback
                    if not manga_update:
                        normalized_notification_title = notification['title'].replace('"', "'")
                        for update in batch:
                            normalized_update_title = update.title.replace('"', "'")
                            if normalized_update_title == normalized_notification_title:
                                manga_update = update
                                logger.info(f"Found manga update by title {notification['title']}")
                                break

                    if manga_update:
                        # Add the manga_update object to the notification for later use
                        notification['manga_update'] = manga_update
                        batch_notifications.append(notification)
                    else:
                        logger.error(f"Could not find matching manga update for {notification['title']} (ID: {notification.get('id', 'Not provided')})")
                        logger.error(f"Available in batch: {[(update.title, update.anilist_id) for update in batch]}")

                all_potential_notifications.extend(batch_notifications)

                # Add a small delay between batches to avoid rate limiting
                if i + batch_size < total_updates:
                    delay = random.uniform(1.0, 2.0)
                    logger.info(f"Waiting {delay:.2f} seconds before next batch...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Error analyzing status changes batch: {e}")
                logger.error(f"Full response was: {response}")

        # Now filter all potential notifications
        logger.info(f"\nStep 2: Filtering {len(all_potential_notifications)} potential notifications")
        
        # Prepare notifications for filtering (remove manga_update object for API call)
        notifications_for_filtering = []
        for notification in all_potential_notifications:
            filtered_notification = {k: v for k, v in notification.items() if k != 'manga_update'}
            notifications_for_filtering.append(filtered_notification)
        
        # Filter the notifications
        filtered_notifications = await self.filter_notifications(notifications_for_filtering)
        
        logger.info(f"Final result: {len(filtered_notifications)} notifications passed the filter")
        
        # Save only the filtered notifications
        saved_notifications = 0
        for filtered_notification in filtered_notifications:
            # Find the original notification with manga_update object
            original_notification = next(
                (n for n in all_potential_notifications 
                 if n.get('id') == filtered_notification.get('id') or 
                    n.get('title') == filtered_notification.get('title')),
                None
            )
            
            if original_notification and 'manga_update' in original_notification:
                self.save_notification(filtered_notification, original_notification['manga_update'])
                saved_notifications += 1
            else:
                logger.error(f"Could not find original notification data for {filtered_notification.get('title', 'Unknown')}")

        # Log analysis completion
        self.log_service_operation(
            "analysis_completed",
            {
                "total_processed": len(self.status_updates),
                "potential_notifications": len(all_potential_notifications),
                "filtered_notifications": len(filtered_notifications),
                "saved_notifications": saved_notifications
            }
        )

        # Clear processed updates
        self.status_updates = []

    async def update_manga_details(self):
        """Main function to update manga details"""
        logger.info("Starting MangaUpdates information update cycle")
        
        # Log the start of the update cycle
        self.log_service_operation(
            "update_cycle_start",
            {"timestamp": datetime.now().isoformat()}
        )
        
        # Check Baby Tyrant specifically for debugging
        try:
            baby_tyrant_check = text("""
                SELECT ml.id_anilist, ml.title_english, ml.external_links,
                       mu.licensed, mu.completed, mu.status
                FROM manga_list ml
                LEFT JOIN mangaupdates_details mu ON ml.id_anilist = mu.anilist_id
                WHERE ml.id_anilist = 162919
            """)
            bt_result = db_session.execute(baby_tyrant_check).first()
            if bt_result:
                logger.info(f"=== BABY TYRANT (162919) DIAGNOSTIC ===")
                logger.info(f"Title: {bt_result.title_english}")
                logger.info(f"External links: {bt_result.external_links}")
                logger.info(f"Licensed: {bt_result.licensed}, Completed: {bt_result.completed}")
                logger.info(f"Status: {bt_result.status}")
                logger.info(f"========================================")
            else:
                logger.warning(f"Baby Tyrant (162919) NOT FOUND in manga_list table!")
        except Exception as e:
            logger.error(f"Error checking Baby Tyrant: {e}")
        
        manga_list = self.get_manga_with_updates_links()
        total_updated = 0
        total_skipped = 0
        
        # Log manga list retrieval
        self.log_service_operation(
            "manga_list_retrieved",
            {"total_manga": len(manga_list)}
        )

        for anilist_id, external_links, licensed, completed, old_status, title in manga_list:
            try:
                logger.info(f"Processing manga {anilist_id}: {title} (Licensed: {licensed}, Completed: {completed})")
                
                # Skip if both licensed and completed
                if not self.should_update_manga(licensed, completed):
                    logger.info(f"Skipping manga {anilist_id} ({title}) - already licensed and completed")
                    total_skipped += 1
                    continue

                mangaupdates_url = self.extract_mangaupdates_url(external_links)
                if not mangaupdates_url:
                    logger.warning(f"No valid MangaUpdates URL extracted for manga {anilist_id} ({title})")
                    logger.debug(f"External links for {anilist_id}: {external_links}")
                    total_skipped += 1
                    continue

                logger.info(f"Fetching details from: {mangaupdates_url}")

                # Use spider instead of API
                try:
                    # Wait for spider to complete and get status
                    new_status = self.run_spider(mangaupdates_url, anilist_id)
                    logger.info(f"New status fetched: {new_status}")

                    # Record the status update
                    update = MangaStatusUpdate(
                        anilist_id=anilist_id,
                        title=title,
                        old_status=old_status,
                        new_status=new_status,
                        timestamp=datetime.now(),
                        url=mangaupdates_url
                    )
                    self.status_updates.append(update)
                    
                    # Log the status update
                    self.log_service_operation(
                        "status_update_recorded",
                        {
                            "anilist_id": anilist_id,
                            "title": title,
                            "old_status": old_status,
                            "new_status": new_status,
                            "url": mangaupdates_url
                        }
                    )

                    # If we have enough updates, analyze them
                    if len(self.status_updates) >= self.batch_size:
                        await self.analyze_status_changes()

                    total_updated += 1
                    logger.info(f"Successfully updated manga {anilist_id}")
                except Exception as spider_error:
                    logger.error(f"Spider failed for manga {anilist_id}: {spider_error}")
                    logger.warning(f"No details retrieved for manga {anilist_id}")

                # Random delay between requests
                delay = self.delay_between_requests
                logger.info(f"Waiting {delay:.2f} seconds before next request...")
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Error processing manga {anilist_id} ({title}): {str(e)}")
                logger.exception("Full exception details:")
                total_skipped += 1

        # Process any remaining status updates that didn't reach batch size
        if len(self.status_updates) > 0:
            logger.info(f"Processing remaining {len(self.status_updates)} status updates...")
            await self.analyze_status_changes()

        total_processed = total_updated + total_skipped
        logger.info(f"Update cycle completed. Total found: {len(manga_list)}, Processed: {total_processed}, Updated: {total_updated}, Skipped: {total_skipped}")
        
        # Log the completion of the update cycle
        self.log_service_operation(
            "update_cycle_completed",
            {
                "total_found": len(manga_list),
                "total_processed": total_processed,
                "total_updated": total_updated,
                "total_skipped": total_skipped,
                "remaining_updates": len(self.status_updates)
            }
        )

async def start_update_service():
    """Initialize and start the update service"""
    service = MangaUpdatesUpdateService()
    
    # Schedule the update to run every 12 hours instead of daily
    schedule.every(12).hours.do(lambda: asyncio.run(service.update_manga_details()))
    logger.info("MangaUpdates update service started - running every 12 hours")
    
    # Run once immediately on startup
    logger.info("Running initial update on startup...")
    await service.update_manga_details()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check schedule every minute

async def test_update_service(limit=5):
    """Test version of the update service with detailed logging"""
    logger.info("Starting MangaUpdates TEST MODE with detailed logging")
    logger.info(f"Testing with limit of {limit} manga entries")
    
    service = MangaUpdatesUpdateService()
    manga_list = service.get_manga_with_updates_links()
    
    logger.info(f"Found total of {len(manga_list)} manga entries with MangaUpdates links")
    logger.info(f"Testing first {min(limit, len(manga_list))} entries")
    
    total_updated = 0
    total_skipped = 0
    all_updates = []

    for anilist_id, external_links, licensed, completed, old_status, title in manga_list[:limit]:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing manga ID: {anilist_id}")
            logger.info(f"Current status - Licensed: {licensed}, Completed: {completed}")

            # Skip if both licensed and completed
            if not service.should_update_manga(licensed, completed):
                logger.info(f"SKIPPING - Manga {anilist_id} is already licensed and completed")
                total_skipped += 1
                continue

            mangaupdates_url = service.extract_mangaupdates_url(external_links)
            if not mangaupdates_url:
                logger.warning(f"No MangaUpdates URL found in external links for manga {anilist_id} ({title})")
                logger.debug(f"External links for {anilist_id}: {external_links}")
                total_skipped += 1
                continue

            logger.info(f"Fetching details from: {mangaupdates_url}")

            try:
                new_status = service.run_spider(mangaupdates_url, anilist_id)
                logger.info(f"New status fetched: {new_status}")

                # Record the status update
                update = MangaStatusUpdate(
                    anilist_id=anilist_id,
                    title=title,
                    old_status=old_status,
                    new_status=new_status,
                    timestamp=datetime.now(),
                    url=mangaupdates_url
                )
                all_updates.append(update)

                total_updated += 1
                logger.info(f"Successfully updated manga {anilist_id}")
            except Exception as spider_error:
                logger.error(f"Spider failed for manga {anilist_id}: {spider_error}")
                logger.warning(f"No details retrieved for manga {anilist_id}")

            # Random delay between requests
            delay = service.delay_between_requests
            logger.info(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)

        except Exception as e:
            logger.error(f"Error processing manga {anilist_id}: {str(e)}")

    logger.info(f"\n{'='*50}")
    logger.info("Test Update Summary:")
    logger.info(f"Total processed: {min(limit, len(manga_list))}")
    logger.info(f"Successfully updated: {total_updated}")
    logger.info(f"Skipped (licensed & completed): {total_skipped}")
    logger.info(f"Failed: {min(limit, len(manga_list)) - total_updated - total_skipped}")

    # Now process all updates in batches
    if all_updates:
        logger.info("\nProcessing all status updates...")
        service.status_updates = all_updates
        await service.analyze_status_changes()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='MangaUpdates Update Service')
    parser.add_argument('--test', action='store_true', help='Run in test mode with detailed logging')
    parser.add_argument('--limit', type=int, default=5, help='Number of manga to process in test mode')
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_update_service(args.limit))
    else:
        asyncio.run(start_update_service())