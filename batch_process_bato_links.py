"""
Batch Process Bato Links
=========================

This script fetches all manga entries with Bato links from the database and processes them
using the existing Bato scraping infrastructure. It's designed to populate Bato data for 
manga that were added before the automatic Bato scraping was implemented.

Features:
- Fetches manga with bato_link from manga_list table
- Skips entries that already have Bato data in bato_manga_details
- Processes each entry using the existing Bato GraphQL scrapers
- Adds random delays between requests to avoid API abuse
- Supports test mode to process only N titles before full run
- Comprehensive logging and error handling
- Progress tracking and statistics

Author: Shiro (for Madrus)
Date: 2025-11-01
"""

import sys
import os
import logging
import argparse
import time
import random
import re
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.functions.class_mangalist import db_session, MangaList
from app.models.bato_models import BatoMangaDetails
from app.scraper.bato_graphql_hidden_api.bato_chapters_list_graphql import BatoChaptersListGraphQL
from app.scraper.bato_graphql_hidden_api.bato_manga_details_graphql import BatoMangaDetailsGraphQL
from app.database_module.bato_repository import BatoRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/batch_bato_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatoBatchProcessor:
    """Processes Bato links from the database in batch with rate limiting."""
    
    def __init__(
        self, 
        min_delay: float = 5.0, 
        max_delay: float = 15.0,
        skip_existing: bool = True,
        verbose: bool = False
    ):
        """
        Initialize the batch processor.
        
        Args:
            min_delay: Minimum delay in seconds between requests
            max_delay: Maximum delay in seconds between requests
            skip_existing: If True, skip manga that already have Bato data
            verbose: Enable verbose logging for scrapers
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.skip_existing = skip_existing
        self.verbose = verbose
        
        # Initialize scrapers
        self.chapters_scraper = BatoChaptersListGraphQL(verbose=verbose)
        self.details_scraper = BatoMangaDetailsGraphQL(verbose=verbose)
        self.bato_repo = BatoRepository()
        
        # Statistics
        self.stats = {
            'total_found': 0,
            'already_processed': 0,
            'successfully_processed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
    def extract_bato_id(self, bato_link: str) -> Optional[str]:
        """
        Extract Bato ID from a Bato link.
        
        Args:
            bato_link: The Bato.to URL
            
        Returns:
            Bato ID as string, or None if not found
        """
        match = re.search(r'/title/(\d+)', bato_link)
        if match:
            return match.group(1)
        return None
    
    def get_manga_with_bato_links(self, limit: Optional[int] = None) -> List[Tuple[int, str, str]]:
        """
        Fetch manga entries that have Bato links from the database.
        
        Args:
            limit: Optional limit on number of entries to fetch
            
        Returns:
            List of tuples (anilist_id, series_name, bato_link)
        """
        try:
            query = db_session.query(
                MangaList.id_anilist,
                MangaList.title_english,
                MangaList.bato_link
            ).filter(
                MangaList.bato_link != '',
                MangaList.bato_link.isnot(None)
            ).order_by(MangaList.last_updated_on_site.desc())
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            # Convert to list of tuples, use title_romaji if english is None
            manga_list = []
            for anilist_id, title_english, bato_link in results:
                # Get full manga entry for fallback title
                if not title_english:
                    manga_entry = db_session.query(MangaList).filter_by(id_anilist=anilist_id).first()
                    title = manga_entry.title_romaji if manga_entry else f"Unknown (ID: {anilist_id})"
                else:
                    title = title_english
                
                manga_list.append((anilist_id, title, bato_link))
            
            logger.info(f"Found {len(manga_list)} manga with Bato links")
            return manga_list
            
        except Exception as e:
            logger.error(f"Error fetching manga with Bato links: {e}")
            logger.error(traceback.format_exc())
            return []
        finally:
            db_session.remove()
    
    def check_if_processed(self, anilist_id: int) -> bool:
        """
        Check if a manga has already been processed (has Bato data).
        
        Args:
            anilist_id: The AniList ID of the manga
            
        Returns:
            True if already processed, False otherwise
        """
        try:
            existing = db_session.query(BatoMangaDetails).filter_by(
                anilist_id=anilist_id
            ).first()
            return existing is not None
        except Exception as e:
            logger.error(f"Error checking if manga {anilist_id} is processed: {e}")
            return False
        finally:
            db_session.remove()
    
    def process_single_manga(
        self, 
        anilist_id: int, 
        series_name: str, 
        bato_link: str
    ) -> bool:
        """
        Process a single manga entry: scrape details and chapters.
        
        This replicates the logic from add_bato_link_route in manga.py
        
        Args:
            anilist_id: The AniList ID
            series_name: The series name
            bato_link: The Bato link
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"=" * 80)
        logger.info(f"Processing: {series_name} (AniList ID: {anilist_id})")
        logger.info(f"Bato Link: {bato_link}")
        
        try:
            # Extract Bato ID
            bato_id = self.extract_bato_id(bato_link)
            if not bato_id:
                logger.error(f"Could not extract Bato ID from link: {bato_link}")
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'anilist_id': anilist_id,
                    'series_name': series_name,
                    'error': 'Invalid Bato link format'
                })
                return False
            
            logger.info(f"Extracted Bato ID: {bato_id}")
            
            # Scrape manga details
            logger.info(f"[1/3] Fetching Bato manga details...")
            details_data = self.details_scraper.scrape_manga_details(bato_id)
            
            if not details_data:
                logger.error(f"Failed to fetch manga details for {series_name}")
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'anilist_id': anilist_id,
                    'series_name': series_name,
                    'error': 'Failed to fetch manga details'
                })
                return False
            
            # Scrape chapters
            logger.info(f"[2/3] Fetching Bato chapters...")
            chapters_result = self.chapters_scraper.scrape_chapters(bato_id, get_manga_title=False)
            chapters_data = chapters_result.get('chapters', [])
            
            logger.info(f"Found {len(chapters_data)} chapters")
            
            # Save manga details to database
            manga_details_dict = {
                'anilist_id': anilist_id,
                'bato_link': bato_link,
                'bato_id': bato_id,
                'name': details_data.get('name', series_name),
                'alt_names': details_data.get('alt_names', []),
                'authors': details_data.get('authors', []),
                'artists': details_data.get('artists', []),
                'genres': details_data.get('genres', []),
                'upload_status': details_data.get('upload_status'),
                'summary': details_data.get('summary'),
                # Rating data
                'stat_score_val': details_data.get('stat_score_val', 0.0),
                'stat_count_votes': details_data.get('stat_count_votes', 0),
                'stat_count_scores': details_data.get('stat_count_scores', []),
                # Statistics
                'stat_count_follows': details_data.get('stat_count_follows', 0),
                'stat_count_reviews': details_data.get('stat_count_reviews', 0),
                'stat_count_post_reply': details_data.get('stat_count_post_reply', 0),
                'stat_count_views_total': details_data.get('stat_count_views_total', 0),
                'stat_count_emotions': details_data.get('stat_count_emotions', []),
                # Publication info
                'orig_lang': details_data.get('orig_lang'),
                'original_status': details_data.get('original_status'),
                'original_pub_from': details_data.get('original_pub_from'),
                'original_pub_till': details_data.get('original_pub_till'),
                'read_direction': details_data.get('read_direction')
            }
            
            self.bato_repo.upsert_manga_details(manga_details_dict)
            logger.info(f"[3/3] Saved Bato manga details")
            
            # Save chapters to database
            if chapters_data:
                # Check if chapters already exist
                existing_chapters = self.bato_repo.get_chapters(anilist_id)
                if existing_chapters:
                    logger.info(f"INFO: Manga already has {len(existing_chapters)} chapters, skipping chapter insert")
                    inserted_count = len(existing_chapters)
                else:
                    chapters_to_insert = []
                    for chapter in chapters_data:
                        chapter_dict = {
                            'anilist_id': anilist_id,
                            'bato_link': bato_link,
                            'bato_chapter_id': chapter.get('bato_chapter_id'),
                            'canonical_chapter_id': chapter.get('canonical_chapter_id'),
                            'chapter_number': chapter.get('chapter_number'),
                            'dname': chapter.get('dname'),
                            'title': chapter.get('title'),
                            'url_path': chapter.get('url_path'),
                            'full_url': chapter.get('full_url'),
                            'date_create': chapter.get('date_create'),
                            'date_public': chapter.get('date_public'),
                            # Statistics
                            'stat_count_views_guest': chapter.get('stat_count_views_guest', 0),
                            'stat_count_views_login': chapter.get('stat_count_views_login', 0),
                            'stat_count_views_total': chapter.get('stat_count_views_total', 0),
                            'stat_count_post_reply': chapter.get('stat_count_post_reply', 0)
                        }
                        chapters_to_insert.append(chapter_dict)
                    
                    inserted_count = self.bato_repo.bulk_insert_chapters(chapters_to_insert)
                    logger.info(f"SUCCESS: Saved {inserted_count} Bato chapters")
            else:
                logger.warning(f"WARNING: No chapters found")
                inserted_count = 0
            
            # Create initial schedule
            existing_schedule = self.bato_repo.get_schedule(anilist_id)
            if existing_schedule:
                logger.info(f"INFO: Schedule already exists, skipping schedule creation")
            else:
                next_scrape_at = datetime.now() + timedelta(hours=24)
                schedule_data = {
                    'anilist_id': anilist_id,
                    'bato_link': bato_link,
                    'next_scrape_at': next_scrape_at,
                    'scraping_interval_hours': 24,
                    'total_chapters_tracked': len(chapters_data) if chapters_data else 0
                }
                self.bato_repo.upsert_schedule(schedule_data)
                logger.info(f"SUCCESS: Created Bato schedule (next scrape: {next_scrape_at})")
            
            # Log the scraping job
            log_data = {
                'anilist_id': anilist_id,
                'bato_link': bato_link,
                'scrape_type': 'batch_initial',
                'status': 'success',
                'chapters_found': len(chapters_data) if chapters_data else 0,
                'new_chapters': len(chapters_data) if chapters_data else 0,
                'duration_seconds': 0,
                'error_message': None
            }
            self.bato_repo.log_scraping_job(log_data)
            
            logger.info(f">> Successfully processed {series_name}")
            logger.info(f"   - Details saved")
            logger.info(f"   - {inserted_count} chapters saved")
            logger.info(f"   - Schedule created")
            
            self.stats['successfully_processed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"!! ERROR processing {series_name}: {e}")
            logger.error(traceback.format_exc())
            
            # Log the failed job
            try:
                log_data = {
                    'anilist_id': anilist_id,
                    'bato_link': bato_link,
                    'scrape_type': 'batch_initial',
                    'status': 'error',
                    'chapters_found': 0,
                    'new_chapters': 0,
                    'duration_seconds': 0,
                    'error_message': str(e)
                }
                self.bato_repo.log_scraping_job(log_data)
            except Exception as log_error:
                logger.error(f"Failed to log error: {log_error}")
            
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'anilist_id': anilist_id,
                'series_name': series_name,
                'error': str(e)
            })
            return False
    
    def random_delay(self):
        """Sleep for a random duration between min_delay and max_delay."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f">> Waiting {delay:.2f} seconds before next request...")
        time.sleep(delay)
    
    def run(self, limit: Optional[int] = None):
        """
        Run the batch processing.
        
        Args:
            limit: Optional limit on number of manga to process (for testing)
        """
        logger.info("=" * 80)
        logger.info(">> Starting Bato Batch Processing")
        logger.info("=" * 80)
        logger.info(f"Configuration:")
        logger.info(f"  - Min delay: {self.min_delay}s")
        logger.info(f"  - Max delay: {self.max_delay}s")
        logger.info(f"  - Skip existing: {self.skip_existing}")
        logger.info(f"  - Limit: {limit if limit else 'None (process all)'}")
        logger.info("")
        
        # Fetch manga with Bato links
        manga_list = self.get_manga_with_bato_links(limit=limit)
        self.stats['total_found'] = len(manga_list)
        
        if not manga_list:
            logger.warning("No manga with Bato links found!")
            return
        
        logger.info(f"Found {len(manga_list)} manga to process")
        logger.info("")
        
        # Process each manga
        for idx, (anilist_id, series_name, bato_link) in enumerate(manga_list, 1):
            logger.info(f"[Progress: {idx}/{len(manga_list)}]")
            
            # Skip if already processed
            if self.skip_existing and self.check_if_processed(anilist_id):
                logger.info(f">> Skipping {series_name} - already processed")
                self.stats['already_processed'] += 1
                continue
            
            # Process the manga
            success = self.process_single_manga(anilist_id, series_name, bato_link)
            
            # Add delay between requests (except after last one)
            if idx < len(manga_list):
                self.random_delay()
        
        # Print final statistics
        self.print_statistics()
    
    def print_statistics(self):
        """Print final processing statistics."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total manga found:         {self.stats['total_found']}")
        logger.info(f"Already processed:         {self.stats['already_processed']}")
        logger.info(f"Successfully processed:    {self.stats['successfully_processed']}")
        logger.info(f"Failed:                    {self.stats['failed']}")
        logger.info(f"Skipped:                   {self.stats['skipped']}")
        logger.info("")
        
        if self.stats['errors']:
            logger.info("!! ERRORS:")
            for error in self.stats['errors']:
                logger.info(f"  - {error['series_name']} (ID: {error['anilist_id']})")
                logger.info(f"    Error: {error['error']}")
        
        logger.info("=" * 80)
        logger.info(">> Batch processing complete!")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Batch process Bato links from the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode - process only 3 manga
  python batch_process_bato_links.py --test 3
  
  # Process all manga with default delays (5-15 seconds)
  python batch_process_bato_links.py
  
  # Process with custom delay range
  python batch_process_bato_links.py --min-delay 10 --max-delay 20
  
  # Process all manga, including those already processed
  python batch_process_bato_links.py --no-skip-existing
  
  # Process first 10 manga with verbose logging
  python batch_process_bato_links.py --limit 10 --verbose
        """
    )
    
    parser.add_argument(
        '--test',
        type=int,
        metavar='N',
        help='Test mode: process only N manga (e.g., --test 3)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        help='Process only N manga (similar to --test)'
    )
    
    parser.add_argument(
        '--min-delay',
        type=float,
        default=5.0,
        help='Minimum delay in seconds between requests (default: 5.0)'
    )
    
    parser.add_argument(
        '--max-delay',
        type=float,
        default=15.0,
        help='Maximum delay in seconds between requests (default: 15.0)'
    )
    
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Process all manga, even those already in bato_manga_details'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging for scrapers'
    )
    
    args = parser.parse_args()
    
    # Determine limit
    limit = args.test or args.limit
    
    # Create processor
    processor = BatoBatchProcessor(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        skip_existing=not args.no_skip_existing,
        verbose=args.verbose
    )
    
    # Run
    try:
        processor.run(limit=limit)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        processor.print_statistics()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
