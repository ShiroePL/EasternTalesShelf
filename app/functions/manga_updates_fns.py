import requests
from urllib.parse import unquote
from bs4 import BeautifulSoup
import json
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MangaUpdatesAPI:
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

    def get_manga_details(self, mangaupdates_link):
        # Fetch the MangaUpdates page
        response = requests.get(mangaupdates_link)
        if response.status_code != 200:
            logging.error(f"Failed to fetch MangaUpdates page: {response.status_code}")
            return None

        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all 'div' elements with class 'sCat'
        sCat_elements = soup.find_all('div', class_='sCat')

        # Initialize a dictionary to store the details
        details = {
            "status_in_country_of_origin": None,
            "licensed_in_english": None,
            "completely_scanlated": None,
            "last_updated": None
        }

        # Loop through the sCat elements to find the desired fields
        for sCat in sCat_elements:
            # Get the text from sCat
            sCat_text = sCat.get_text(strip=True).lower()
            
            # The sContent is the next sibling
            sContent = sCat.find_next_sibling('div', class_='sContent')
            if not sContent:
                continue
            
            # Get the text from sContent
            sContent_text = sContent.get_text(separator=' ', strip=True)  # separator=' ' to handle <BR> tags

            # Match for different categories (case insensitive, flexible formatting)
            if 'status in country of origin' in sCat_text:
                details['status_in_country_of_origin'] = sContent_text
            elif 'licensed (in english)' in sCat_text:
                details['licensed_in_english'] = sContent_text
            elif 'completely scanlated?' in sCat_text:
                details['completely_scanlated'] = sContent_text
            elif 'last updated' in sCat_text:
                details['last_updated'] = sContent_text

        # Clean up the details dictionary by removing None values
        details = {k: v for k, v in details.items() if v is not None}

        if details:
            logging.info(f"Extracted Manga Details: {details}")
            return details
        else:
            logging.error("Could not find the desired details in the MangaUpdates page.")
            return None


