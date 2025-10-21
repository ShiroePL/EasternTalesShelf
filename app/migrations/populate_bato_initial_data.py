"""
MIGRATION SCRIPT - INITIAL SETUP ONLY
This script was used for initial data population and is kept for reference.

Only run this if:
- Setting up a fresh database
- Onboarding new manga with bato_link
- Recreating data after a database reset

Current status: Initial population completed
Last run: [date you ran it]

Usage:
    doppler run -- python app/migrations/populate_bato_initial_data.py --limit 2
"""

"""
Initial Data Population Script for Bato Notification System

This script:
1. Queries all manga_list entries with valid bato_link
2. Extracts bato_id from bato_link URL
3. Scrapes initial chapter data and manga details
4. Creates initial BatoScrapingSchedule entries
5. Does NOT create notifications (initial load)

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5

Usage:
    # Process all manga with bato_link
    doppler run -- python app/migrations/populate_bato_initial_data.py
    
    # Process only first 2 manga (for testing)
    doppler run -- python app/migrations/populate_bato_initial_data.py --limit 2
    
    # Process only 1 manga
    
"""

import sys
import os
import re
import argparse
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.functions.class_mangalist import db_session, MangaList, engine
from app.scraper.bato_graphql_hidden_api.bato_chapters_list_graphql import BatoChaptersListGraphQL
from app.scraper.bato_graphql_hidden_api.bato_manga_details_graphql import BatoMangaDetailsGraphQL
from app.database_module.bato_repository import BatoRepository
from app.models.bato_models import BatoScrapingSchedule
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_bato_id(bato_link: str) -> str:
    """
    Extract bato_id from bato_link URL
    Example: https://batotwo.com/title/110100-... -> 110100
    
    Requirement 1.2: Extract bato_id from URL
    """
    match = re.search(r'/title/(\d+)', bato_link)
    if match:
        return match.group(1)
    return None


def populate_initial_data(limit=None):
    """
    Main function to populate initial data for all manga with bato_link
    
    Args:
        limit (int, optional): Maximum number of manga to process. None = process all
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    logger.info("="*60)
    logger.info("Starting Bato Initial Data Population")
    if limit:
        logger.info(f"LIMIT: Processing maximum {limit} manga")
    logger.info("="*60)
    
    # Query all manga with bato_link
    try:
        query = db_session.query(MangaList).filter(
            MangaList.bato_link != '',
            MangaList.bato_link.isnot(None)
        )
        
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
        
        manga_list = query.all()
        
        total_with_bato_link = db_session.query(MangaList).filter(
            MangaList.bato_link != '',
            MangaList.bato_link.isnot(None)
        ).count()
        
        logger.info(f"Found {total_with_bato_link} total manga with bato_link")
        if limit:
            logger.info(f"Processing first {len(manga_list)} manga (limit={limit})")
        
        if len(manga_list) == 0:
            logger.warning("No manga found with bato_link. Nothing to populate.")
            logger.info("Add bato_link to manga entries in manga_list table first.")
            return
            
    except Exception as e:
        logger.error(f"Error querying manga_list: {e}")
        return
    
    # Initialize scrapers
    chapters_scraper = BatoChaptersListGraphQL()
    details_scraper = BatoMangaDetailsGraphQL()
    repository = BatoRepository()
    
    # Statistics
    stats = {
        'total': len(manga_list),
        'success': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Process each manga
    for idx, manga in enumerate(manga_list, 1):
        logger.info(f"\n[{idx}/{stats['total']}] Processing: {manga.title_english or manga.title_romaji}")
        logger.info(f"  AniList ID: {manga.id_anilist}")
        logger.info(f"  Bato Link: {manga.bato_link}")
        
        try:
            # Extract bato_id
            bato_id = extract_bato_id(manga.bato_link)
            if not bato_id:
                logger.error(f"  ✗ Could not extract bato_id from URL")
                stats['failed'] += 1
                continue
            
            logger.info(f"  Bato ID: {bato_id}")
            
            # Check if already processed
            existing_schedule = repository.get_schedule(manga.id_anilist)
            if existing_schedule:
                logger.info(f"  ⊙ Already has schedule, skipping...")
                stats['skipped'] += 1
                continue
            
            # Scrape manga details
            logger.info(f"  → Scraping manga details...")
            details_data = details_scraper.scrape_manga_details(bato_id)
            
            if not details_data:
                logger.error(f"  ✗ Failed to scrape manga details")
                stats['failed'] += 1
                continue
            
            # Store manga details (map API field names to database field names)
            manga_details = {
                'anilist_id': manga.id_anilist,
                'bato_link': manga.bato_link,
                'bato_id': bato_id,
                'name': details_data.get('name', ''),
                'alt_names': details_data.get('alt_names', []),
                'authors': details_data.get('authors', []),
                'artists': details_data.get('artists', []),
                'genres': details_data.get('genres', []),
                'orig_lang': details_data.get('orig_lang', ''),
                'original_status': details_data.get('original_status', 'unknown'),
                'original_pub_from': details_data.get('original_pub_from'),
                'original_pub_till': details_data.get('original_pub_till'),
                'upload_status': details_data.get('upload_status', 'unknown'),
                'read_direction': details_data.get('read_direction', 'ltr'),
                'summary': details_data.get('summary', ''),
                'stat_score_val': details_data.get('stat_score_val'),
                'stat_count_votes': details_data.get('stat_count_votes', 0),
                'stat_count_scores': details_data.get('stat_count_scores', []),
                'stat_count_follows': details_data.get('stat_count_follows', 0),
                'stat_count_reviews': details_data.get('stat_count_reviews', 0),
                'stat_count_post_reply': details_data.get('stat_count_post_reply', 0),
                'stat_count_views_total': details_data.get('stat_count_views_total', 0),
                'stat_count_emotions': details_data.get('stat_count_emotions', [])
            }
            
            repository.upsert_manga_details(manga_details)
            logger.info(f"  ✓ Manga details saved")
            
            # Scrape chapters
            logger.info(f"  → Scraping chapters...")
            chapters_result = chapters_scraper.scrape_chapters(bato_id, get_manga_title=False)
            chapters_data = chapters_result.get('chapters', [])
            
            if not chapters_data or len(chapters_data) == 0:
                logger.warning(f"  ⚠ No chapters found")
            else:
                # Transform and store chapters (match BatoChapters model fields exactly)
                chapters_to_insert = []
                for chapter in chapters_data:
                    chapters_to_insert.append({
                        'anilist_id': manga.id_anilist,
                        'bato_link': manga.bato_link,
                        'bato_chapter_id': chapter.get('bato_chapter_id', ''),
                        'chapter_number': chapter.get('chapter_number', 0),
                        'dname': chapter.get('dname', ''),
                        'title': chapter.get('title'),
                        'url_path': chapter.get('url_path', ''),
                        'full_url': chapter.get('full_url', ''),
                        'date_public': chapter.get('date_public'),
                        'date_create': chapter.get('date_create'),
                        'stat_count_views_guest': chapter.get('stat_count_views_guest', 0),
                        'stat_count_views_login': chapter.get('stat_count_views_login', 0),
                        'stat_count_views_total': chapter.get('stat_count_views_total', 0),
                        'stat_count_post_reply': chapter.get('stat_count_post_reply', 0)
                    })
                
                # Bulk insert chapters
                # Note: Initial load doesn't create notifications - that's handled by the scraping service
                inserted_count = repository.bulk_insert_chapters(chapters_to_insert)
                
                logger.info(f"  ✓ Inserted {inserted_count} chapters")
            
            # Create initial scraping schedule
            logger.info(f"  → Creating scraping schedule...")
            schedule_data = {
                'anilist_id': manga.id_anilist,
                'bato_link': manga.bato_link,
                'scraping_interval_hours': 24,  # Default 24 hours
                'next_scrape_at': datetime.now() + timedelta(hours=24),
                'last_scraped_at': datetime.now(),
                'priority': 1,
                'is_active': True
            }
            
            repository.upsert_schedule(schedule_data)
            logger.info(f"  ✓ Schedule created (next scrape in 24h)")
            
            # Create log entry for initial population (so admin panel shows data)
            logger.info(f"  → Creating scraper log entry...")
            log_data = {
                'anilist_id': manga.id_anilist,
                'bato_link': manga.bato_link,
                'scrape_type': 'initial',
                'status': 'success',
                'chapters_found': len(chapters_data),
                'new_chapters': len(chapters_data),  # All chapters are "new" on initial load
                'duration_seconds': 0.0,  # Not tracked for initial load
                'scraped_at': datetime.now()
            }
            repository.log_scraping_job(log_data)
            logger.info(f"  ✓ Log entry created")
            
            stats['success'] += 1
            logger.info(f"  ✓ SUCCESS")
            
        except Exception as e:
            logger.error(f"  ✗ Error processing manga: {e}")
            stats['failed'] += 1
            continue
    
    # Final statistics
    logger.info("\n" + "="*60)
    logger.info("MIGRATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total manga processed: {stats['total']}")
    logger.info(f"✓ Successfully populated: {stats['success']}")
    logger.info(f"⊙ Skipped (already exists): {stats['skipped']}")
    logger.info(f"✗ Failed: {stats['failed']}")
    logger.info("="*60)
    
    if stats['success'] > 0:
        logger.info("\n✓ Initial data population completed!")
        logger.info("The BatoScrapingService will now monitor these manga automatically.")
    
    # Cleanup
    db_session.remove()


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Populate initial Bato data for manga with bato_link',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all manga
  python app/migrations/populate_bato_initial_data.py
  
  # Process only 2 manga (for testing)
  python app/migrations/populate_bato_initial_data.py --limit 2
  
  # With doppler
  doppler run -- python app/migrations/populate_bato_initial_data.py --limit 1
        """
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of manga to process (default: process all)'
    )
    
    args = parser.parse_args()
    
    try:
        populate_initial_data(limit=args.limit)
    except KeyboardInterrupt:
        logger.info("\n\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nMigration failed with error: {e}")
        sys.exit(1)
