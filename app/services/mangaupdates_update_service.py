import logging
import random
import time
from datetime import datetime
import schedule
from app.functions.sqlalchemy_fns import save_manga_details
from app.functions.class_mangalist import db_session
from sqlalchemy import text
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for
from app.functions.manga_updates_spider import MangaUpdatesSpider

# Initialize crochet for Scrapy to work with async code
setup()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MangaUpdatesUpdateService:
    def __init__(self):
        self.delay_between_requests = random.uniform(2.0, 4.0)  # random delay between 2.0-4.0 seconds with decimal precision

    @wait_for(timeout=30.0)
    def run_spider(self, url, anilist_id):
        """Run the MangaUpdates spider for a given URL"""
        runner = CrawlerRunner()
        deferred = runner.crawl(MangaUpdatesSpider, start_url=url, anilist_id=anilist_id)
        return deferred

    def get_manga_with_updates_links(self):
        """Fetch all manga entries that have MangaUpdates links"""
        try:
            query = text("""
                SELECT ml.id_anilist, ml.external_links, mu.licensed, mu.completed
                FROM manga_list ml
                LEFT JOIN mangaupdates_details mu ON ml.id_anilist = mu.anilist_id
                WHERE ml.external_links LIKE '%mangaupdates.com%'
            """)
            
            result = db_session.execute(query)
            return [(row.id_anilist, row.external_links, row.licensed, row.completed) 
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

    def update_manga_details(self):
        """Main function to update manga details"""
        logger.info("Starting MangaUpdates information update cycle")
        
        manga_list = self.get_manga_with_updates_links()
        total_updated = 0
        total_skipped = 0

        for anilist_id, external_links, licensed, completed in manga_list:
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
                    self.run_spider(mangaupdates_url, anilist_id)
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

def start_update_service():
    """Initialize and start the update service"""
    service = MangaUpdatesUpdateService()
    
    # Schedule the update to run daily at a specific time (e.g., 3 AM)
    schedule.every().day.at("03:00").do(service.update_manga_details)
    
    logger.info("MangaUpdates update service started")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check schedule every minute

def test_update_service(limit=5):
    """Test version of the update service with detailed logging"""
    logger.info("Starting MangaUpdates TEST MODE with detailed logging")
    logger.info(f"Testing with limit of {limit} manga entries")
    
    service = MangaUpdatesUpdateService()
    manga_list = service.get_manga_with_updates_links()
    
    logger.info(f"Found total of {len(manga_list)} manga entries with MangaUpdates links")
    logger.info(f"Testing first {min(limit, len(manga_list))} entries")
    
    total_updated = 0
    total_skipped = 0

    for anilist_id, external_links, licensed, completed in manga_list[:limit]:
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

            # Use spider instead of API
            try:
                service.run_spider(mangaupdates_url, anilist_id)
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

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='MangaUpdates Update Service')
    parser.add_argument('--test', action='store_true', help='Run in test mode with detailed logging')
    parser.add_argument('--limit', type=int, default=5, help='Number of manga to process in test mode')
    args = parser.parse_args()
    
    if args.test:
        test_update_service(args.limit)
    else:
        start_update_service() 