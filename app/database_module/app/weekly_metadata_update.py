"""
Weekly Metadata Update Script
This script updates manga metadata (release status, chapter counts, etc.) for all titles in the database.
It skips titles that are already marked as FINISHED to optimize API calls.
Designed to run weekly via cron job in the database_module container.
"""

import json
import time
import requests
import mysql.connector
from db_config import conn
from datetime import datetime
import api_keys
from typing import List, Dict, Optional

# ANSI escape sequences for colors
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Configuration
BATCH_SIZE = 50  # AniList allows up to 50 IDs per query
RATE_LIMIT_DELAY = 1  # Delay between requests in seconds
ANILIST_API_URL = 'https://graphql.anilist.co'

# Statistics
stats = {
    'total_checked': 0,
    'updated': 0,
    'already_finished': 0,
    'errors': 0,
    'start_time': None,
    'end_time': None
}


def log(message: str, color: str = RESET):
    """Print colored log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {color}{message}{RESET}")


def get_manga_ids_to_update() -> List[tuple]:
    """
    Fetch all manga IDs from database.
    Returns list of tuples: (id_anilist, current_status)
    Skips manga that are already marked as FINISHED in the database.
    """
    cursor = conn.cursor()
    
    # Get all manga that are NOT finished (to save API calls)
    # We'll still check finished ones occasionally, but less frequently
    query = f"""
        SELECT id_anilist, status, title_romaji, title_english 
        FROM {api_keys.table_name} 
        WHERE status != 'FINISHED' OR status IS NULL
        ORDER BY last_updated_on_site ASC
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    
    log(f"Found {len(results)} manga to check (excluding already FINISHED titles)", GREEN)
    return results


def fetch_manga_metadata(anilist_ids: List[int]) -> Dict:
    """
    Fetch metadata for multiple manga from AniList API
    Returns dict with manga data keyed by ID
    """
    # Build the query with multiple IDs
    # Note: This query fetches MEDIA data, but we need mediaList data to get updatedAt
    # We need to fetch from the user's list to get the updatedAt timestamp
    # This requires a different query structure
    query = '''
    query ($ids: [Int]) {
        Page(perPage: 50) {
            media(id_in: $ids, type: MANGA) {
                id
                idMal
                title {
                    romaji
                    english
                }
                status
                chapters
                volumes
                description
                coverImage {
                    large
                }
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                genres
                externalLinks {
                    url
                }
                countryOfOrigin
            }
        }
    }
    '''
    
    variables = {'ids': anilist_ids}
    
    try:
        response = requests.post(
            ANILIST_API_URL,
            json={'query': query, 'variables': variables},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        if 'errors' in data:
            log(f"API returned errors: {data['errors']}", RED)
            return {}
        
        # Convert to dict keyed by ID for easy lookup
        media_list = data.get('data', {}).get('Page', {}).get('media', [])
        return {media['id']: media for media in media_list}
        
    except requests.exceptions.RequestException as e:
        log(f"API request failed: {e}", RED)
        stats['errors'] += 1
        return {}


def format_date(date_obj: Optional[Dict]) -> str:
    """Convert AniList date object to string"""
    if not date_obj:
        return 'media not ended'
    
    year = date_obj.get('year')
    month = date_obj.get('month')
    day = date_obj.get('day')
    
    if not year and not month and not day:
        return 'media not ended'
    
    year_str = str(year) if year else 'None'
    month_str = str(month) if month else 'None'
    day_str = str(day) if day else 'None'
    
    return f"{year_str}-{month_str}-{day_str}"


def update_manga_metadata(media_data: Dict) -> bool:
    """
    Update a single manga's metadata in the database
    Returns True if updated, False if skipped or error
    """
    try:
        cursor = conn.cursor()
        
        # Parse data from API
        media_id = media_data['id']
        id_mal = media_data.get('idMal') or 0
        
        # Titles
        title_english = str(media_data['title'].get('english') or '').replace("'", '"')
        title_romaji = str(media_data['title'].get('romaji') or '').replace("'", '"')
        
        # Status and counts
        status = media_data.get('status') or 'RELEASING'
        chapters = media_data.get('chapters') or 0
        volumes = media_data.get('volumes') or 0
        
        # Description
        description = str(media_data.get('description') or '').replace('<br><br>', '<br>').replace("'", '"')
        
        # Cover image
        cover_image = media_data.get('coverImage', {}).get('large') or ''
        
        # Country
        country = media_data.get('countryOfOrigin') or ''
        
        # Dates
        media_start_date = format_date(media_data.get('startDate'))
        media_end_date = format_date(media_data.get('endDate'))
        
        # Genres
        genres = json.dumps(media_data.get('genres', []))
        
        # External links
        external_links = json.dumps([link['url'] for link in media_data.get('externalLinks', [])])
        
        # MAL URL
        mal_url = f"https://myanimelist.net/manga/{id_mal}" if id_mal else ''
        
        # Update query - only update metadata fields, not user progress
        # IMPORTANT: We do NOT update last_updated_on_site here because that's used
        # for sorting on the website (shows recently edited/added manga)
        # The weekly metadata update should not affect the user's sort order
        update_query = f"""
            UPDATE {api_keys.table_name} SET
                id_mal = %s,
                title_english = %s,
                title_romaji = %s,
                status = %s,
                all_chapters = %s,
                all_volumes = %s,
                description = %s,
                cover_image = %s,
                mal_url = %s,
                country_of_origin = %s,
                media_start_date = %s,
                media_end_date = %s,
                genres = %s,
                external_links = %s
            WHERE id_anilist = %s
        """
        
        update_record = (
            id_mal, title_english, title_romaji, status,
            chapters, volumes, description, cover_image,
            mal_url, country, media_start_date, media_end_date,
            genres, external_links, media_id
        )
        
        cursor.execute(update_query, update_record)
        conn.commit()
        cursor.close()
        
        log(f"✓ Updated: {title_romaji} (ID: {media_id}) - Status: {status}", CYAN)
        stats['updated'] += 1
        return True
        
    except mysql.connector.Error as e:
        log(f"Database error updating manga {media_data.get('id')}: {e}", RED)
        stats['errors'] += 1
        return False


def process_batch(batch: List[tuple]) -> None:
    """Process a batch of manga IDs"""
    # Extract just the IDs
    anilist_ids = [item[0] for item in batch]
    
    log(f"Fetching metadata for {len(anilist_ids)} manga...", YELLOW)
    
    # Fetch metadata from API
    media_dict = fetch_manga_metadata(anilist_ids)
    
    if not media_dict:
        log("No data received from API for this batch", RED)
        return
    
    # Update each manga
    for manga_tuple in batch:
        manga_id = manga_tuple[0]
        current_status = manga_tuple[1]
        title = manga_tuple[2] or manga_tuple[3] or f"ID {manga_id}"
        
        stats['total_checked'] += 1
        
        if manga_id in media_dict:
            media_data = media_dict[manga_id]
            new_status = media_data.get('status')
            
            # Log status changes
            if current_status != new_status:
                log(f"Status changed for '{title}': {current_status} → {new_status}", MAGENTA)
            
            update_manga_metadata(media_data)
        else:
            log(f"No data found for '{title}' (ID: {manga_id})", YELLOW)
            stats['errors'] += 1
    
    # Rate limiting
    time.sleep(RATE_LIMIT_DELAY)


def print_statistics():
    """Print final statistics"""
    duration = (stats['end_time'] - stats['start_time']).total_seconds()
    
    print("\n" + "=" * 60)
    log("WEEKLY METADATA UPDATE COMPLETED", GREEN)
    print("=" * 60)
    log(f"Total manga checked: {stats['total_checked']}", BLUE)
    log(f"Successfully updated: {stats['updated']}", GREEN)
    log(f"Errors encountered: {stats['errors']}", RED if stats['errors'] > 0 else YELLOW)
    log(f"Duration: {duration:.2f} seconds", CYAN)
    log(f"Average speed: {stats['total_checked']/duration:.2f} manga/second", CYAN)
    print("=" * 60 + "\n")


def main():
    """Main execution function"""
    stats['start_time'] = datetime.now()
    
    log("=" * 60, CYAN)
    log("WEEKLY METADATA UPDATE - STARTED", GREEN)
    log("=" * 60, CYAN)
    log(f"Table: {api_keys.table_name}", BLUE)
    
    try:
        # Get all manga IDs to update
        manga_list = get_manga_ids_to_update()
        
        if not manga_list:
            log("No manga found to update", YELLOW)
            return
        
        # Process in batches
        total_batches = (len(manga_list) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(manga_list), BATCH_SIZE):
            batch = manga_list[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            log(f"\n--- Processing batch {batch_num}/{total_batches} ---", YELLOW)
            process_batch(batch)
        
    except mysql.connector.Error as e:
        log(f"Database connection error: {e}", RED)
        stats['errors'] += 1
        
    except Exception as e:
        log(f"Unexpected error: {e}", RED)
        stats['errors'] += 1
        
    finally:
        stats['end_time'] = datetime.now()
        print_statistics()
        
        # Close connection
        if conn.is_connected():
            conn.close()
            log("Database connection closed", BLUE)


if __name__ == "__main__":
    main()
