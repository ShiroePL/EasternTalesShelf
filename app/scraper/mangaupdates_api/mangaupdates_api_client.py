"""
MangaUpdates API Client
A fast, efficient replacement for the Scrapy spider that uses the official REST API
"""
import requests
import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MangaUpdatesAPIClient:
    """Client for interacting with MangaUpdates REST API."""
    
    def __init__(self):
        self.base_url = "https://api.mangaupdates.com/v1"
        self.web_base_url = "https://www.mangaupdates.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': 'application/json',
        }
    
    def extract_slug_from_url(self, url: str) -> Optional[str]:
        """
        Extract the series slug from a MangaUpdates URL.
        
        Examples:
            https://www.mangaupdates.com/series/m9j8pqm/what-should-i-do -> m9j8pqm
            https://www.mangaupdates.com/series/izo08g8 -> izo08g8
        
        Args:
            url: The MangaUpdates URL
            
        Returns:
            The series slug or None if not found
        """
        try:
            # Pattern: /series/{slug}/optional-title or /series/{slug}
            match = re.search(r'/series/([a-z0-9]+)', url.lower())
            if match:
                slug = match.group(1)
                logger.info(f"Extracted slug '{slug}' from URL: {url}")
                return slug
            else:
                logger.warning(f"Could not extract slug from URL: {url}")
                return None
        except Exception as e:
            logger.error(f"Error extracting slug from URL {url}: {e}")
            return None
    
    def slug_to_id(self, slug: str) -> Optional[str]:
        """
        Convert a MangaUpdates slug to numeric series ID.
        
        The API requires numeric IDs, but URLs use slugs.
        We need to fetch the HTML page to find the numeric ID in the RSS link.
        
        Args:
            slug: The series slug (e.g., 'm9j8pqm')
            
        Returns:
            The numeric series ID or None if not found
        """
        try:
            url = f"{self.web_base_url}/series/{slug}"
            logger.info(f"Fetching page to convert slug '{slug}' to ID: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Look for the RSS feed URL which contains the numeric ID
            # Example: https://api.mangaupdates.com/v1/series/48465726286/rss
            match = re.search(r'https://api\.mangaupdates\.com/v1/series/(\d+)/rss', response.text)
            
            if match:
                series_id = match.group(1)
                logger.info(f"Successfully converted slug '{slug}' to ID: {series_id}")
                return series_id
            else:
                logger.warning(f"Could not find numeric ID for slug '{slug}' in page HTML")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error converting slug '{slug}' to ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error converting slug '{slug}' to ID: {e}")
            return None
    
    def get_series_by_id(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch series details using the numeric series ID.
        
        Args:
            series_id: The numeric series ID
            
        Returns:
            Dictionary containing series data or None if failed
        """
        try:
            url = f"{self.base_url}/series/{series_id}"
            logger.info(f"Fetching series data from API: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched series data for ID {series_id}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching series {series_id} from API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching series {series_id}: {e}")
            return None
    
    def get_series_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch series details using a MangaUpdates URL.
        
        This is the main method that combines slug extraction, ID conversion, and data fetching.
        
        Args:
            url: The MangaUpdates URL (e.g., https://www.mangaupdates.com/series/m9j8pqm/...)
            
        Returns:
            Dictionary containing series data or None if failed
        """
        try:
            # Step 1: Extract slug from URL
            slug = self.extract_slug_from_url(url)
            if not slug:
                logger.error(f"Failed to extract slug from URL: {url}")
                return None
            
            # Step 2: Convert slug to numeric ID
            series_id = self.slug_to_id(slug)
            if not series_id:
                logger.error(f"Failed to convert slug '{slug}' to numeric ID")
                return None
            
            # Step 3: Fetch series data using the ID
            data = self.get_series_by_id(series_id)
            if not data:
                logger.error(f"Failed to fetch series data for ID {series_id}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error in get_series_by_url for {url}: {e}")
            return None
    
    def extract_spider_compatible_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from API response in a format compatible with the old spider.
        
        This maintains backward compatibility with existing save_manga_details() function.
        
        Args:
            api_data: The full API response
            
        Returns:
            Dictionary with keys: status_in_country_of_origin, licensed_in_english, 
                                  completely_scanlated, last_updated
        """
        try:
            # Extract the status field (e.g., "311 Chapters (Complete)")
            status = api_data.get('status', '')
            
            # Extract licensed status (boolean in API)
            licensed = api_data.get('licensed', False)
            licensed_text = 'Yes' if licensed else 'No'
            
            # Extract completed status (boolean in API)
            completed = api_data.get('completed', False)
            completed_text = 'Yes' if completed else 'No'
            
            # Extract last updated timestamp
            last_updated_obj = api_data.get('last_updated', {})
            if isinstance(last_updated_obj, dict):
                timestamp = last_updated_obj.get('timestamp', '')
                # Convert Unix timestamp to readable format if needed
                if timestamp:
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        last_updated = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        last_updated = str(timestamp)
                else:
                    last_updated = ''
            else:
                last_updated = str(last_updated_obj) if last_updated_obj else ''
            
            spider_compatible_data = {
                'status_in_country_of_origin': status,
                'licensed_in_english': licensed_text,
                'completely_scanlated': completed_text,
                'last_updated': last_updated
            }
            
            logger.info(f"Extracted spider-compatible data: {spider_compatible_data}")
            return spider_compatible_data
            
        except Exception as e:
            logger.error(f"Error extracting spider-compatible data: {e}")
            return {
                'status_in_country_of_origin': '',
                'licensed_in_english': 'No',
                'completely_scanlated': 'No',
                'last_updated': ''
            }
    
    def get_series_full_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch series data and return BOTH the full API data and spider-compatible data.
        
        Args:
            url: The MangaUpdates URL
            
        Returns:
            Dictionary with 'api_data' (full API response) and 'spider_data' (compatible format)
        """
        try:
            api_data = self.get_series_by_url(url)
            if not api_data:
                return None
            
            spider_data = self.extract_spider_compatible_data(api_data)
            
            return {
                'api_data': api_data,
                'spider_data': spider_data
            }
            
        except Exception as e:
            logger.error(f"Error in get_series_full_data for {url}: {e}")
            return None


# Convenience function for quick usage
def fetch_manga_updates_data(url: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to fetch MangaUpdates data from a URL.
    
    Args:
        url: The MangaUpdates URL
        
    Returns:
        Dictionary with spider-compatible data or None if failed
    """
    client = MangaUpdatesAPIClient()
    result = client.get_series_full_data(url)
    if result:
        return result['spider_data']
    return None


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    test_url = "https://www.mangaupdates.com/series/m9j8pqm/what-should-i-do-with-my-brother"
    
    client = MangaUpdatesAPIClient()
    result = client.get_series_full_data(test_url)
    
    if result:
        print("\n=== Spider-Compatible Data ===")
        print(result['spider_data'])
        
        print("\n=== Full API Data (sample) ===")
        api_data = result['api_data']
        print(f"Title: {api_data.get('title')}")
        print(f"Type: {api_data.get('type')}")
        print(f"Year: {api_data.get('year')}")
        print(f"Rating: {api_data.get('bayesian_rating')}")
        print(f"Genres: {[g.get('genre') for g in api_data.get('genres', [])][:5]}")
    else:
        print("Failed to fetch data")
