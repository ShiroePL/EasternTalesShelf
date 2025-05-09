import logging
import os
import random
import time
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
Compare the statuses carefully - look for changes in chapter counts, season completions, or status changes.
If there are few notification for one manhwa, glue them to one notificiation.
Example of significant change: "S4: 36 Chapters (116~)" to "S4: 40 Chapters (116~155)" indicates season 4 completion.

Here are the status changes to analyze:

"""

class MangaUpdatesUpdateService:
    def __init__(self):
        self.delay_between_requests = random.uniform(4.0, 7.0)  # random delay between 4.0-7.0 seconds with decimal precision
        self.status_updates: List[MangaStatusUpdate] = []
        self.batch_size = 2
        self.engine = create_engine(DATABASE_URI, pool_recycle=3600, pool_pre_ping=True)

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
            query = text("""
                SELECT ml.id_anilist, ml.external_links, mu.licensed, mu.completed,
                       mu.status as old_status,
                       ml.title_english
                FROM manga_list ml  -- Always use production table
                LEFT JOIN mangaupdates_details mu ON ml.id_anilist = mu.anilist_id
                WHERE ml.external_links LIKE '%mangaupdates.com%'
            """)
            
            result = db_session.execute(query)
            return [(row.id_anilist, row.external_links, row.licensed, row.completed,
                     row.old_status, row.title_english) 
                    for row in result]
        except Exception as e:
            logger.error(f"Error fetching manga with updates links: {e}")
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

    async def analyze_status_changes(self):
        """Analyze status changes using LLM in batches of 3"""
        if len(self.status_updates) < 1:
            logger.info("No updates for analysis")
            return

        logger.info("Starting status change analysis")
        
        # Process updates in batches of 3
        batch_size = 3
        total_updates = len(self.status_updates)
        
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
                # Call Groq API
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
                
                # Process each notification with fallback to ID matching
                for notification in analysis.get('notifications', []):
                    logger.info(f"Processing notification: {notification}")
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
                        self.save_notification(notification, manga_update)
                    else:
                        logger.error(f"Could not find matching manga update for {notification['title']} (ID: {notification.get('id', 'Not provided')})")
                        logger.error(f"Available in batch: {[(update.title, update.anilist_id) for update in batch]}")

                # Add a small delay between batches to avoid rate limiting
                if i + batch_size < total_updates:
                    delay = random.uniform(1.0, 2.0)
                    logger.info(f"Waiting {delay:.2f} seconds before next batch...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Error analyzing status changes batch: {e}")
                logger.error(f"Full response was: {response}")

        # Clear processed updates
        self.status_updates = []

    async def update_manga_details(self):
        """Main function to update manga details"""
        logger.info("Starting MangaUpdates information update cycle")
        
        manga_list = self.get_manga_with_updates_links()
        total_updated = 0
        total_skipped = 0

        for anilist_id, external_links, licensed, completed, old_status, title in manga_list:
            try:
                # Skip if both licensed and completed
                if not self.should_update_manga(licensed, completed):
                    logger.info(f"Skipping manga {anilist_id} - already licensed and completed")
                    total_skipped += 1
                    continue

                mangaupdates_url = self.extract_mangaupdates_url(external_links)
                if not mangaupdates_url:
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
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error processing manga {anilist_id}: {str(e)}")

        logger.info(f"Update cycle completed. Updated: {total_updated}, Skipped: {total_skipped}")

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
                logger.warning(f"No MangaUpdates URL found in external links for manga {anilist_id}")
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