import requests
from urllib.parse import urlparse, unquote, parse_qs
from bs4 import BeautifulSoup
import json
import re
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MangaUpdatesAPI:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

    def extract_series_name(self, url):
        logging.info(f"Extracting series name from {url}")
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'id' in query_params:
            logging.info("URL contains 'id' parameter, returning None.")
            return None
        else:
            series_name = parsed_url.path.split('/')[-1]
            return series_name

    def search_series(self, series_name):
        logging.info(f"Searching for {series_name}")
        api_url = "https://api.mangaupdates.com/v1/series/search"
        data = {"search": series_name}
        response = requests.post(api_url, json=data, headers=self.headers)
        results = response.json().get("results", [])
        
        for result in results:
            record = result.get("record", {})
            if record.get("title").lower().replace(' ', '-') == series_name.lower():
                return record.get("series_id")
        
        # If no exact match, return the first result's series_id
        if results:
            logging.info(f"No exact match found, returning first result's series_id: {results[0].get('record', {}).get('series_id')}")
            return results[0].get("record", {}).get("series_id")
        return None

    def get_series_details(self, series_id):
        logging.info(f"Getting details for series {series_id}")
        api_url = f"https://api.mangaupdates.com/v1/series/{series_id}?unrenderedFields=true"
        response = requests.get(api_url, headers=self.headers)
        details = response.json()
        
        return {
            "series_id": details.get("series_id"),
            "status": details.get("status"),
            "licensed": details.get("licensed"),
            "completed": details.get("completed"),
            "last_updated": {
                "timestamp": details.get("last_updated", {}).get("timestamp")                
            }
        }

    def get_manga_details(self, url, series_name=None):
        extracted_series_name = self.extract_series_name(url)
        
        if extracted_series_name is None:
            if series_name is None:
                raise ValueError("Series name is required when URL contains 'id' parameter")
        else:
            series_name = extracted_series_name

        series_id = self.search_series(series_name)
        if not series_id:
            return None
        
        details = self.get_series_details(series_id)
        return details
    
    def extract_links_from_bato(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        astro_islands = soup.find_all('astro-island')
        extracted_links = []
        for island in astro_islands:
            if 'Display_Text_ResInfo' in island.get('opts', ''):
                props = json.loads(island['props'].replace('&quot;', '"'))
                links_str = props.get('code', [None, None])[1]
                if links_str:
                    links = links_str.split('\n')
                    for link in links:
                        cleaned_link = link.split('] ')[-1].strip()
                        cleaned_link = unquote(cleaned_link)
                        url_match = re.search(r'https?://[^\s]+', cleaned_link)
                        if url_match:
                            url = url_match.group(0)
                            if all(ord(char) < 128 for char in url):
                                extracted_links.append(url)
                                logging.info(f"Extracted Link: {url}")
        return extracted_links
