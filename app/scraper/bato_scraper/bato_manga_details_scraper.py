"""
FINAL VERSION - Playwright + BeautifulSoup COMBO!
Playwright ładuje JS, BeautifulSoup parsuje HTML.
"""
import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import Dict
import json
import html

class BatoMangaDetailsScraper:
    """Scraper do wyciągania szczegółowych info o mandze."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        
    async def __aenter__(self):
        """Setup browser context."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        # Block tylko images, zostaw resztę
        await self.context.route(
            "**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2}",
            lambda route: route.abort()
        )
        return self
        
    async def __aexit__(self, *args):
        """Cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_manga_details(self, manga_id: str) -> Dict:
        """
        Scrape wszystkie details mangi.
        Używamy Playwright do loadowania JS, potem BeautifulSoup do parsowania.
        """
        page = await self.context.new_page()
        
        try:
            url = f'https://batotwo.com/title/{manga_id}'
            print(f"🔍 Fetching manga details from {url}...")
            
            # Wait for networkidle = all JS loaded
            await page.goto(url, wait_until='networkidle', timeout=20000)
            
            # Get HTML content
            html_content = await page.content()
            
            print("✅ Page loaded, parsing with BeautifulSoup...")
            
            # Parse z BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # --- EXTRACT FROM ASTRO-ISLAND PROPS ---
            # Znajdź wszystkie astro-island elements i weź ten z największym props
            astro_islands = soup.find_all('astro-island')
            
            if not astro_islands:
                print("⚠️ No astro-island found, trying alternative extraction...")
                return await self._extract_from_html(soup, manga_id)
            
            # Find the astro-island with the largest props (contains manga data)
            largest_island = None
            largest_props = ""
            
            for island in astro_islands:
                props_str = island.get('props', '')
                if len(props_str) > len(largest_props):
                    largest_props = props_str
                    largest_island = island
            
            if not largest_island or len(largest_props) < 100:
                print("⚠️ No valid astro-island props found, trying alternative extraction...")
                return await self._extract_from_html(soup, manga_id)
            
            # Decode HTML entities
            props_decoded = html.unescape(largest_props)
            
            print(f"📦 Found props data ({len(props_decoded)} chars)")
            
            # Parse data from props JSON
            result = self._parse_props(props_decoded, manga_id)
            
            # FALLBACK: Extract visible rating from HTML (gdy props nie zadziałają)
            result = self._extract_from_visible_html(soup, result)
            
            print(f"✅ Scraped: {result['title']}")
            print(f"   Rating: {result['rating']['average']}/10 ({result['rating']['votes']} votes)")
            print(f"   Genres: {', '.join(result['genres'][:3])}...")
            print(f"   Status: {result['publication']['status']} ({result['publication']['years']})")
            
            return result
            
        except Exception as e:
            print(f"❌ Error scraping details: {e}")
            await page.screenshot(path=f'error_{manga_id[:10]}.png')
            import traceback
            traceback.print_exc()
            raise
        finally:
            await page.close()
    
    def _parse_props(self, props_str: str, manga_id: str) -> Dict:
        """Parse data z astro-island props."""
        
        # Helper function do wyciągania wartości
        def extract_value(pattern, default="Unknown"):
            match = re.search(pattern, props_str)
            return match.group(1) if match else default
        
        def extract_array(pattern):
            match = re.search(pattern, props_str)
            if not match:
                return []
            array_str = match.group(1)
            # Extract wszystkie stringi z array
            items = re.findall(r'\[0,\\"([^\\]+)\\"', array_str)
            return [item for item in items if item]
        
        # Title
        title = extract_value(r'"name":\[0,"([^"]+)"')
        title = title.replace('\\u0026', '&')
        
        # Alt titles
        alt_titles = extract_array(r'"altNames":\[1,"(\[\[.*?\]\])"')
        
        # Authors  
        authors = extract_array(r'"authors":\[1,"(\[\[.*?\]\])"')
        
        # Artists
        artists = extract_array(r'"artists":\[1,"(\[\[.*?\]\])"')
        
        # Genres
        genres_raw = extract_array(r'"genres":\[1,"(\[\[.*?\]\])"')
        genres = [g.replace('_', ' ').title() for g in genres_raw]
        
        # Original language
        orig_lang = extract_value(r'"origLang":\[0,"(\w+)"', '')
        lang_names = {'ko': 'Korean', 'ja': 'Japanese', 'zh': 'Chinese', 'en': 'English'}
        orig_lang = lang_names.get(orig_lang, orig_lang.upper())
        
        # Publication status
        pub_status = extract_value(r'"originalStatus":\[0,"(\w+)"')
        pub_status = pub_status.upper()
        
        # Publication years
        year_from = extract_value(r'"originalPubFrom":\[0,"(\d+)"', '?')
        year_till_match = re.search(r'"originalPubTill":\[0,(null|"(\d+)")', props_str)
        year_till = '?' if year_till_match and 'null' in year_till_match.group(0) else (year_till_match.group(2) if year_till_match and year_till_match.group(2) else '?')
        pub_years = f"{year_from}-{year_till}"
        
        # Read direction
        read_dir_code = extract_value(r'"readDirection":\[0,"(\w+)"', 'ltr')
        read_dir = "Left to Right" if read_dir_code == "ltr" else "Right to Left"
        
        # Rating
        rating_avg = None
        rating_match = re.search(r'"stat_score_val":\[0,([\d.]+)\]', props_str)
        if rating_match:
            rating_avg = round(float(rating_match.group(1)), 2)
        
        # Votes
        votes = 0
        votes_match = re.search(r'"stat_count_votes":\[0,(\d+)\]', props_str)
        if votes_match:
            votes = int(votes_match.group(1))
        
        # Rating distribution
        rating_distribution = {}
        scores_match = re.search(r'"stat_count_scores":\[1,"(.+?)"\]', props_str)
        if scores_match:
            scores_str = scores_match.group(1)
            # Extract star ratings
            star_pattern = r'\\\\"field\\\\":\[0,\\\\"(\d+)\\\\"\],\\\\"count\\\\":\[0,(\d+)\]'
            star_matches = re.findall(star_pattern, scores_str)
            
            total_votes = sum(int(count) for _, count in star_matches) or 1
            
            for star, count in star_matches:
                percentage = (int(count) / total_votes) * 100
                rating_distribution[f"{star}★"] = {
                    'count': int(count),
                    'percentage': round(percentage, 1)
                }
        
        # Stats
        stats = {}
        
        # Follows
        follows_match = re.search(r'"stat_count_follows":\[0,(\d+)\]', props_str)
        if follows_match:
            count = int(follows_match.group(1))
            stats['follows'] = self._format_number(count)
            stats['follows_raw'] = count
        
        # Reviews
        reviews_match = re.search(r'"stat_count_reviews":\[0,(\d+)\]', props_str)
        if reviews_match:
            stats['reviews'] = int(reviews_match.group(1))
        
        # Comments
        comments_match = re.search(r'"stat_count_post_reply":\[0,(\d+)\]', props_str)
        if comments_match:
            count = int(comments_match.group(1))
            stats['comments'] = self._format_number(count)
            stats['comments_raw'] = count
        
        # Views (total - d000)
        views_pattern = r'\\\\"field\\\\":\[0,\\\\"d000\\\\"\],\\\\"count\\\\":\[0,(\d+)\]'
        views_match = re.search(views_pattern, props_str)
        if views_match:
            count = int(views_match.group(1))
            stats['views'] = self._format_number(count)
            stats['views_raw'] = count
        
        # Also try to get views from visible HTML as backup
        # This will be filled in _extract_from_visible_html if not present
        
        # Emotions
        emotions = {}
        emotion_pattern = r'\\\\"field\\\\":\[0,\\\\"(upvote|funny|love|surprised|angry|sad)\\\\"\],\\\\"count\\\\":\[0,(\d+)\]'
        emotion_matches = re.findall(emotion_pattern, props_str)
        
        for emotion, count in emotion_matches:
            emotions[emotion] = int(count)
        
        # Summary
        summary = ""
        # Try to find summary in the summary object
        summary_match = re.search(r'"summary":\[0,\{[^}]*"text":\[0,"([^"]+)"\]', props_str)
        if summary_match:
            summary = summary_match.group(1)
            # Replace common HTML entities and unicode issues
            summary = summary.replace('\\u0026', '&')
            summary = summary.replace('\\u2019', "'")
            summary = summary.replace('\\u2026', '...')
            summary = summary.replace('\\u201c', '"')
            summary = summary.replace('\\u201d', '"')
            # Fix encoding issues from Latin-1 to UTF-8
            try:
                # If it's showing â instead of apostrophes, it's likely a UTF-8 byte sequence interpreted as Latin-1
                if 'â' in summary or 'Ã' in summary:
                    summary = summary.encode('latin1').decode('utf-8')
            except:
                pass
        
        # BATO upload status
        upload_status = extract_value(r'"uploadStatus":\[0,"(\w+)"', 'Unknown').upper()
        
        return {
            'manga_id': manga_id,
            'title': title,
            'alt_titles': alt_titles,
            'authors': authors,
            'artists': artists,
            'genres': genres,
            'original_language': orig_lang,
            'publication': {
                'status': pub_status,
                'years': pub_years
            },
            'bato_upload_status': upload_status,
            'read_direction': read_dir,
            'rating': {
                'average': rating_avg,
                'votes': votes,
                'distribution': rating_distribution
            },
            'stats': stats,
            'emotions': emotions,
            'summary': summary
        }
    
    def _extract_from_visible_html(self, soup: BeautifulSoup, result: Dict) -> Dict:
        """
        Fallback extraction z widocznego HTML.
        Uzupełnia dane, które nie zostały wyciągnięte z props.
        """
        # BATO Upload Status - z "BATO Upload Status: Ongoing"
        if 'bato_upload_status' not in result or result['bato_upload_status'] == 'UNKNOWN':
            status_div = soup.find('div', string=re.compile(r'BATO.*Status:'))
            if status_div:
                status_span = status_div.find('span', class_='font-bold')
                if status_span:
                    result['bato_upload_status'] = status_span.get_text(strip=True).upper()
        
        # Views - z <i name="eye">...<span>157.7K</span>
        if 'views' not in result.get('stats', {}):
            eye_icon = soup.find('i', attrs={'name': 'eye'})
            if eye_icon:
                parent = eye_icon.find_parent('span')
                if parent:
                    views_span = parent.find('span', class_='ml-1')
                    if views_span:
                        views_text = views_span.get_text(strip=True)
                        result['stats']['views'] = views_text
                        # Try to parse raw number
                        try:
                            views_text_clean = views_text.replace('K', '000').replace('M', '000000').replace('.', '')
                            result['stats']['views_raw'] = int(views_text_clean)
                        except:
                            pass
        
        # Rating average - z <span class="text-yellow-500">8.7</span>
        if not result['rating']['average']:
            rating_elem = soup.find('span', class_='text-yellow-500')
            if rating_elem:
                try:
                    rating_text = rating_elem.get_text(strip=True)
                    if re.match(r'^\d+\.\d+$', rating_text):
                        result['rating']['average'] = float(rating_text)
                except:
                    pass
        
        # Votes - z "1359<!-- --> votes"
        if not result['rating']['votes']:
            votes_elem = soup.find('div', class_='whitespace-nowrap', string=re.compile(r'votes'))
            if votes_elem:
                votes_match = re.search(r'(\d+)', votes_elem.get_text())
                if votes_match:
                    result['rating']['votes'] = int(votes_match.group(1))
        
        # Star distribution - z <progress> elements
        if not result['rating']['distribution']:
            progress_elements = soup.find_all('progress', class_='progress-primary')
            star_distribution = {}
            
            for progress in progress_elements:
                parent = progress.find_parent('div', class_='flex')
                if parent:
                    # Find star number (5, 4, 3, 2, 1)
                    star_elem = parent.find('span')
                    # Find percentage
                    percentage_elem = parent.find('span', class_='font-mono')
                    
                    if star_elem and percentage_elem:
                        star = star_elem.get_text(strip=True)
                        percentage_text = percentage_elem.get_text(strip=True).replace('%', '').strip()
                        
                        try:
                            percentage = float(percentage_text)
                            # Calculate count from percentage and total votes
                            if result['rating']['votes'] > 0:
                                count = int((percentage / 100) * result['rating']['votes'])
                                star_distribution[f"{star}★"] = {
                                    'count': count,
                                    'percentage': percentage
                                }
                        except:
                            pass
            
            if star_distribution:
                result['rating']['distribution'] = star_distribution
        
        # Emotions - z images i labels
        if not result['emotions']:
            emotions_map = {
                'upvote': 'awesome',
                'funny': 'funny', 
                'love': 'love',
                'surprised': 'scared',
                'angry': 'angry',
                'sad': 'sad'
            }
            
            emotions = {}
            
            # Find emotion images
            emotion_imgs = soup.find_all('img', src=re.compile(r'/emotions/'))
            for img in emotion_imgs:
                # Get emotion type from src
                src = img.get('src', '')
                for emotion_key in emotions_map.keys():
                    if emotion_key in src:
                        # Find the SVG path data with numbers (from chart)
                        # This is tricky - we need to look at the chart labels
                        break
            
            # Alternative: look for text labels in the chart
            label_texts = soup.find_all('text', class_='recharts-label')
            emotion_values = []
            for label in label_texts:
                tspan = label.find('tspan')
                if tspan:
                    try:
                        value = int(tspan.get_text(strip=True))
                        emotion_values.append(value)
                    except:
                        pass
            
            # Map values to emotions (order: upvote, funny, love, surprised, angry, sad)
            emotion_keys = ['upvote', 'funny', 'love', 'surprised', 'angry', 'sad']
            for i, key in enumerate(emotion_keys):
                if i < len(emotion_values):
                    emotions[key] = emotion_values[i]
            
            if emotions:
                result['emotions'] = emotions
        
        return result
    
    async def _extract_from_html(self, soup: BeautifulSoup, manga_id: str) -> Dict:
        """Fallback extraction bezpośrednio z HTML (gdy nie ma astro-island)."""
        # Prosty fallback
        base_result = {
            'manga_id': manga_id,
            'title': "Could not extract",
            'alt_titles': [],
            'authors': [],
            'artists': [],
            'genres': [],
            'original_language': '',
            'publication': {'status': 'Unknown', 'years': 'Unknown'},
            'bato_upload_status': 'UNKNOWN',
            'read_direction': 'Unknown',
            'rating': {'average': None, 'votes': 0, 'distribution': {}},
            'stats': {},
            'emotions': {},
            'summary': ''
        }
        
        # Try to extract from visible HTML
        return self._extract_from_visible_html(soup, base_result)
    
    def _format_number(self, num: int) -> str:
        """Format number to K/M format."""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)


async def main():
    """Test manga details scraper."""
    async with BatoMangaDetailsScraper() as scraper:
        result = await scraper.scrape_manga_details('110100-the-villainess-s-stationery-shop-official')
        
        # Save to JSON
        with open('manga_details_output.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved to manga_details_output.json")
        print(f"\n📊 Full output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(main())
