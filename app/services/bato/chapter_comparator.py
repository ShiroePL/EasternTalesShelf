"""
ChapterComparator - New Chapter Detection Service

Compares scraped chapter data against database records to identify new chapters.
Implements logic for single chapter vs batch notification determination.

Uses canonical_chapter_id (extracted from URL, e.g., 'ch_0', 'ch_112') as the stable
identifier to detect truly new chapters, even when Bato re-uploads with new chapter IDs.

Requirements:
- 2.1: Compare canonical_chapter_id values against existing records
- 2.3: Determine batch updates (3+ chapters)
- 6.6: Enforce unique constraint on (bato_link, canonical_chapter_id)
- 6.7: Handle chapter re-uploads with new bato_chapter_id
"""

from typing import List, Dict, Set
from app.database_module.bato_repository import BatoRepository
import logging

logger = logging.getLogger(__name__)


class ChapterComparator:
    """
    Service for detecting new chapters by comparing scraped data with database.
    
    This class handles the core logic for identifying which chapters from a scraping
    operation are actually new and need to trigger notifications.
    """
    
    def __init__(self):
        """Initialize the ChapterComparator with repository access."""
        self.repository = BatoRepository()
    
    def find_new_chapters(self, anilist_id: int, scraped_chapters: List[Dict]) -> List[Dict]:
        """
        Identify chapters not in database by comparing canonical_chapter_id.
        
        This is the main method for new chapter detection. It efficiently queries
        existing canonical chapter IDs and filters the scraped data to find only new chapters.
        
        canonical_chapter_id is extracted from the URL (e.g., 'ch_0', 'ch_112') and is
        stable across chapter re-uploads. This prevents duplicate notifications when
        Bato re-uploads a chapter with a new bato_chapter_id.
        
        Args:
            anilist_id: AniList manga ID
            scraped_chapters: List of chapter dictionaries from scraper with fields:
                - bato_chapter_id (required): Unique chapter identifier (may change on re-upload)
                - canonical_chapter_id (required): Stable identifier from URL (ch_0, ch_1, etc.)
                - chapter_number (required): Position in list
                - dname (required): Display name
                - title (optional): Chapter subtitle
                - url_path (required): Relative URL
                - full_url (required): Complete chapter URL
                - date_create (optional): Creation timestamp
                - date_public (optional): Publication timestamp
                - stat_count_views_guest (optional): Guest view count
                - stat_count_views_login (optional): Login view count
                - stat_count_views_total (optional): Total view count
                - stat_count_post_reply (optional): Comment count
        
        Returns:
            List of new chapter dictionaries (not in database)
            
        Example:
            >>> comparator = ChapterComparator()
            >>> scraped = [
            ...     {'bato_chapter_id': '2068065', 'canonical_chapter_id': 'ch_112', 'dname': 'Chapter 112', ...},
            ...     {'bato_chapter_id': '2068066', 'canonical_chapter_id': 'ch_113', 'dname': 'Chapter 113', ...}
            ... ]
            >>> new_chapters = comparator.find_new_chapters(123456, scraped)
            >>> len(new_chapters)
            2
        """
        if not scraped_chapters:
            logger.info(f"No scraped chapters provided for anilist_id {anilist_id}")
            return []
        
        try:
            # Get existing canonical chapter IDs from database
            existing_canonical_ids = self.get_existing_canonical_chapter_ids(anilist_id)
            
            logger.info(
                f"Comparing {len(scraped_chapters)} scraped chapters against "
                f"{len(existing_canonical_ids)} existing chapters for anilist_id {anilist_id}"
            )
            
            # Filter out chapters that already exist (by canonical_chapter_id)
            # Skip chapters without canonical_chapter_id (shouldn't happen with updated scraper)
            new_chapters = [
                chapter for chapter in scraped_chapters
                if chapter.get('canonical_chapter_id') 
                and chapter.get('canonical_chapter_id') not in existing_canonical_ids
            ]
            
            # Warn about chapters without canonical_chapter_id
            missing_canonical_id = [
                ch for ch in scraped_chapters 
                if not ch.get('canonical_chapter_id')
            ]
            if missing_canonical_id:
                logger.warning(
                    f"Found {len(missing_canonical_id)} chapters without canonical_chapter_id "
                    f"for anilist_id {anilist_id}. These will be treated as new chapters."
                )
                # Treat them as new (fallback behavior)
                new_chapters.extend(missing_canonical_id)
            
            if new_chapters:
                logger.info(
                    f"Found {len(new_chapters)} new chapters for anilist_id {anilist_id}: "
                    f"{[ch.get('dname', 'Unknown') for ch in new_chapters]}"
                )
            else:
                logger.info(f"No new chapters found for anilist_id {anilist_id}")
            
            return new_chapters
            
        except Exception as e:
            logger.error(f"Error finding new chapters for anilist_id {anilist_id}: {e}")
            return []
    
    def get_existing_canonical_chapter_ids(self, anilist_id: int) -> Set[str]:
        """
        Get set of canonical_chapter_id already in database for efficient comparison.
        
        This method provides O(1) lookup time for checking if a chapter exists,
        which is critical for performance when comparing large chapter lists.
        
        Uses canonical_chapter_id (e.g., 'ch_0', 'ch_112') instead of bato_chapter_id
        to correctly identify existing chapters even when they've been re-uploaded.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            Set of canonical_chapter_id strings
            
        Example:
            >>> comparator = ChapterComparator()
            >>> existing = comparator.get_existing_canonical_chapter_ids(123456)
            >>> 'ch_112' in existing
            True
        """
        try:
            canonical_ids = self.repository.get_existing_canonical_chapter_ids(anilist_id)
            logger.debug(f"Retrieved {len(canonical_ids)} existing canonical chapter IDs for anilist_id {anilist_id}")
            return canonical_ids
        except Exception as e:
            logger.error(f"Error getting existing canonical chapter IDs for anilist_id {anilist_id}: {e}")
            return set()
    
    def get_existing_chapter_ids(self, anilist_id: int) -> Set[str]:
        """
        Get set of bato_chapter_id already in database for efficient comparison.
        
        DEPRECATED: Use get_existing_canonical_chapter_ids() instead for deduplication.
        This method is kept for backward compatibility only.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            Set of bato_chapter_id strings
        """
        try:
            chapter_ids = self.repository.get_existing_chapter_ids(anilist_id)
            logger.debug(f"Retrieved {len(chapter_ids)} existing chapter IDs for anilist_id {anilist_id}")
            return chapter_ids
        except Exception as e:
            logger.error(f"Error getting existing chapter IDs for anilist_id {anilist_id}: {e}")
            return set()
    
    def should_create_batch_notification(self, new_chapters: List[Dict]) -> bool:
        """
        Determine if multiple chapters should be batched into one notification.
        
        According to requirement 2.3, when 3 or more new chapters are detected
        in a single scraping operation, they should be grouped into a batch
        notification rather than creating individual notifications.
        
        Args:
            new_chapters: List of new chapter dictionaries
            
        Returns:
            True if batch notification should be created (3+ chapters),
            False if individual notifications should be created
            
        Example:
            >>> comparator = ChapterComparator()
            >>> chapters = [{'bato_chapter_id': '1'}, {'bato_chapter_id': '2'}]
            >>> comparator.should_create_batch_notification(chapters)
            False
            >>> chapters.append({'bato_chapter_id': '3'})
            >>> comparator.should_create_batch_notification(chapters)
            True
        """
        chapter_count = len(new_chapters)
        is_batch = chapter_count >= 3
        
        if is_batch:
            logger.info(
                f"Batch notification recommended: {chapter_count} new chapters detected"
            )
        else:
            logger.debug(
                f"Individual notifications recommended: {chapter_count} new chapter(s) detected"
            )
        
        return is_batch
    
    def validate_chapter_data(self, chapter: Dict) -> bool:
        """
        Validate that a chapter dictionary has all required fields.
        
        This is a helper method to ensure data integrity before processing.
        
        Args:
            chapter: Chapter dictionary to validate
            
        Returns:
            True if all required fields are present, False otherwise
        """
        required_fields = ['bato_chapter_id', 'canonical_chapter_id', 'chapter_number', 'dname', 'full_url']
        
        for field in required_fields:
            if field not in chapter or chapter[field] is None:
                logger.warning(f"Chapter missing required field '{field}': {chapter}")
                return False
        
        return True
    
    def filter_valid_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """
        Filter chapter list to only include valid chapters with required fields.
        
        Args:
            chapters: List of chapter dictionaries
            
        Returns:
            List of valid chapter dictionaries
        """
        valid_chapters = [ch for ch in chapters if self.validate_chapter_data(ch)]
        
        if len(valid_chapters) < len(chapters):
            logger.warning(
                f"Filtered out {len(chapters) - len(valid_chapters)} invalid chapters"
            )
        
        return valid_chapters
    
    def get_chapter_summary(self, chapters: List[Dict]) -> str:
        """
        Generate a human-readable summary of chapters for logging/notifications.
        
        Args:
            chapters: List of chapter dictionaries
            
        Returns:
            Summary string (e.g., "Chapters 110-113" or "Chapter 110")
        """
        if not chapters:
            return "No chapters"
        
        if len(chapters) == 1:
            return chapters[0].get('dname', 'Unknown chapter')
        
        # Try to extract chapter numbers for range
        chapter_names = [ch.get('dname', '') for ch in chapters]
        
        if len(chapters) <= 3:
            return ", ".join(chapter_names)
        else:
            return f"{chapter_names[0]} - {chapter_names[-1]} ({len(chapters)} chapters)"
