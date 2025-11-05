"""
Repair Script - Fix last_updated_on_site timestamps
This script fetches the correct updatedAt from AniList and restores the proper timestamps
for manga that were incorrectly updated by the weekly metadata update.
"""

import json
import time
import requests
import mysql.connector
from db_config import conn
from datetime import datetime
import api_keys
from typing import List, Dict

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
RATE_LIMIT_DELAY = 3  # Delay between requests in seconds
ANILIST_API_URL = 'https://graphql.anilist.co'
USER_ID = api_keys.anilist_id

# Statistics
stats = {
    'total_checked': 0,
    'updated': 0,
    'errors': 0,
    'start_time': None,
    'end_time': None
}


def log(message: str, color: str = RESET):
    """Print colored log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {color}{message}{RESET}")


def get_all_manga_ids() -> List[tuple]:
    """
    Fetch all manga IDs from database
    Returns list of tuples: (id_anilist, title_romaji, title_english)
    """
    cursor = conn.cursor()
    
    query = f"""
        SELECT id_anilist, title_romaji, title_english, last_updated_on_site
        FROM {api_keys.table_name}
        ORDER BY id_anilist ASC
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    
    log(f"Found {len(results)} manga to repair", GREEN)
    return results


def fetch_medialist_data(anilist_ids: List[int]) -> Dict:
    """
    Fetch mediaList data (including updatedAt) from AniList API
    Returns dict with manga data keyed by ID
    """
    # Build the query to get mediaList data (which includes updatedAt)
    query = '''
    query ($userId: Int, $ids: [Int]) {
        Page(perPage: 50) {
            mediaList(userId: $userId, mediaId_in: $ids, type: MANGA) {
                mediaId
                updatedAt
                media {
                    title {
                        romaji
                    }
                }
            }
        }
    }
    '''
    
    variables = {'userId': USER_ID, 'ids': anilist_ids}
    
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
        
        # Convert to dict keyed by mediaId for easy lookup
        media_list = data.get('data', {}).get('Page', {}).get('mediaList', [])
        return {item['mediaId']: item for item in media_list}
        
    except requests.exceptions.RequestException as e:
        log(f"API request failed: {e}", RED)
        stats['errors'] += 1
        return {}


def update_timestamp(media_id: int, updated_at: int, title: str) -> bool:
    """
    Update the last_updated_on_site timestamp for a manga
    Returns True if updated, False if error
    """
    try:
        cursor = conn.cursor()
        
        # Convert Unix timestamp to datetime
        updated_at_datetime = datetime.fromtimestamp(updated_at)
        updated_at_str = updated_at_datetime.strftime('%Y-%m-%d %H:%M:%S')
        
        # Update query
        update_query = f"""
            UPDATE {api_keys.table_name}
            SET last_updated_on_site = %s
            WHERE id_anilist = %s
        """
        
        cursor.execute(update_query, (updated_at_str, media_id))
        conn.commit()
        cursor.close()
        
        log(f"✓ Repaired: {title} (ID: {media_id}) - Timestamp: {updated_at_str}", CYAN)
        stats['updated'] += 1
        return True
        
    except mysql.connector.Error as e:
        log(f"Database error updating manga {media_id}: {e}", RED)
        stats['errors'] += 1
        return False


def process_batch(batch: List[tuple]) -> None:
    """Process a batch of manga IDs"""
    # Extract just the IDs
    anilist_ids = [item[0] for item in batch]
    
    log(f"Fetching updatedAt timestamps for {len(anilist_ids)} manga...", YELLOW)
    
    # Fetch mediaList data from API
    medialist_dict = fetch_medialist_data(anilist_ids)
    
    if not medialist_dict:
        log("No data received from API for this batch", RED)
        return
    
    # Update each manga
    for manga_tuple in batch:
        manga_id = manga_tuple[0]
        title_romaji = manga_tuple[1]
        title_english = manga_tuple[2]
        current_timestamp = manga_tuple[3]
        
        title = title_romaji or title_english or f"ID {manga_id}"
        
        stats['total_checked'] += 1
        
        if manga_id in medialist_dict:
            medialist_item = medialist_dict[manga_id]
            updated_at = medialist_item.get('updatedAt')
            
            if updated_at:
                # Convert current timestamp to Unix for comparison
                if current_timestamp:
                    if isinstance(current_timestamp, str):
                        current_dt = datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S')
                    else:
                        current_dt = current_timestamp
                    current_unix = int(time.mktime(current_dt.timetuple()))
                else:
                    current_unix = 0
                
                # Only update if different
                if current_unix != updated_at:
                    update_timestamp(manga_id, updated_at, title)
                else:
                    log(f"= Skipped: {title} (already correct)", BLUE)
            else:
                log(f"⚠ No updatedAt for '{title}' (ID: {manga_id})", YELLOW)
        else:
            log(f"⚠ Not found in your list: '{title}' (ID: {manga_id})", YELLOW)
    
    # Rate limiting
    time.sleep(RATE_LIMIT_DELAY)


def print_statistics():
    """Print final statistics"""
    duration = (stats['end_time'] - stats['start_time']).total_seconds()
    
    print("\n" + "=" * 60)
    log("TIMESTAMP REPAIR COMPLETED", GREEN)
    print("=" * 60)
    log(f"Total manga checked: {stats['total_checked']}", BLUE)
    log(f"Successfully updated: {stats['updated']}", GREEN)
    log(f"Errors encountered: {stats['errors']}", RED if stats['errors'] > 0 else YELLOW)
    log(f"Duration: {duration:.2f} seconds", CYAN)
    if stats['total_checked'] > 0:
        log(f"Average speed: {stats['total_checked']/duration:.2f} manga/second", CYAN)
    print("=" * 60 + "\n")


def main():
    """Main execution function"""
    stats['start_time'] = datetime.now()
    
    log("=" * 60, CYAN)
    log("TIMESTAMP REPAIR SCRIPT - STARTED", GREEN)
    log("=" * 60, CYAN)
    log(f"Table: {api_keys.table_name}", BLUE)
    log(f"User ID: {USER_ID}", BLUE)
    
    try:
        # Get all manga IDs to repair
        manga_list = get_all_manga_ids()
        
        if not manga_list:
            log("No manga found to repair", YELLOW)
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
