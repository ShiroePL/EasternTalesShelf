"""
Test script for weekly metadata update
Processes only a small sample (5 manga) to verify functionality
"""

import json
import time
import requests
import mysql.connector
from db_config import conn
from datetime import datetime
import api_keys

# ANSI colors
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

ANILIST_API_URL = 'https://graphql.anilist.co'
TEST_LIMIT = 5  # Only test with 5 manga

print(f"{CYAN}{'='*60}{RESET}")
print(f"{GREEN}Testing Weekly Metadata Update (Sample: {TEST_LIMIT} manga){RESET}")
print(f"{CYAN}{'='*60}{RESET}\n")

try:
    cursor = conn.cursor()
    
    # Get 5 manga that are not finished
    query = f"""
        SELECT id_anilist, status, title_romaji, title_english 
        FROM {api_keys.table_name} 
        WHERE status != 'FINISHED' OR status IS NULL
        LIMIT {TEST_LIMIT}
    """
    
    cursor.execute(query)
    manga_list = cursor.fetchall()
    
    if not manga_list:
        print(f"{YELLOW}No manga found for testing{RESET}")
        exit()
    
    print(f"{GREEN}Found {len(manga_list)} manga to test:{RESET}")
    for manga in manga_list:
        title = manga[2] or manga[3] or f"ID {manga[0]}"
        print(f"  - {title} (Current status: {manga[1]})")
    
    print(f"\n{CYAN}Fetching metadata from AniList...{RESET}")
    
    # Fetch from AniList
    anilist_ids = [m[0] for m in manga_list]
    
    query_gql = '''
    query ($ids: [Int]) {
        Page(perPage: 50) {
            media(id_in: $ids, type: MANGA) {
                id
                title {
                    romaji
                    english
                }
                status
                chapters
                volumes
            }
        }
    }
    '''
    
    response = requests.post(
        ANILIST_API_URL,
        json={'query': query_gql, 'variables': {'ids': anilist_ids}},
        timeout=30
    )
    
    data = response.json()
    media_list = data.get('data', {}).get('Page', {}).get('media', [])
    
    print(f"\n{GREEN}API Response:{RESET}")
    for media in media_list:
        print(f"\n  Title: {media['title']['romaji']}")
        print(f"  Status: {media['status']}")
        print(f"  Chapters: {media['chapters']}")
        print(f"  Volumes: {media['volumes']}")
    
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{GREEN}Test completed successfully!{RESET}")
    print(f"{YELLOW}To run the full update, use: python weekly_metadata_update.py{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")
    
except Exception as e:
    print(f"{RESET}Error: {e}")

finally:
    if conn.is_connected():
        conn.close()
