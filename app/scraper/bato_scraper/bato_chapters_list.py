"""
ENHANCED Bato Chapters List Scraper
Playwright + BeautifulSoup for comprehensive chapter data extraction
"""
import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import Dict, List
import json
from datetime import datetime, timezone

class BatoChaptersListScraper:
    """Scraper do wyciągania pełnej listy rozdziałów."""
    
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
        
        # Block images/fonts for speed
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
    
    async def scrape_chapters(self, manga_id: str) -> Dict:
        """
        Scrape ALL chapters with full details.
        """
        page = await self.context.new_page()
        
        try:
            url = f'https://batotwo.com/title/{manga_id}'
            print(f"🔍 Fetching chapters from {url}...")
            
            # Wait for networkidle = all JS loaded
            await page.goto(url, wait_until='networkidle', timeout=20000)
            
            # Wait for chapter list
            await page.wait_for_selector('div[name="chapter-list"]', timeout=10000)
            
            # Get HTML content
            html_content = await page.content()
            
            print("✅ Page loaded, parsing chapters with BeautifulSoup...")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Extract manga title
            title_elem = soup.find('h3', class_='item-title')
            if not title_elem:
                title_elem = soup.find('h1')
            if not title_elem:
                title_elem = soup.find(string=re.compile(r'Chapter'))
                if title_elem:
                    # Try to find parent with title
                    parent = title_elem.find_parent('div')
                    if parent:
                        title_parts = []
                        for text in parent.stripped_strings:
                            if 'chapter' not in text.lower():
                                title_parts.append(text)
                        manga_title = ' '.join(title_parts[:1]) if title_parts else "Unknown"
                    else:
                        manga_title = "Unknown"
                else:
                    manga_title = "Unknown"
            else:
                manga_title = title_elem.get_text(strip=True)
            
            # If title is still not good, try astro-island props (same as details scraper)
            if manga_title == "Unknown" or manga_title == "More..." or len(manga_title) < 3:
                astro_islands = soup.find_all('astro-island')
                for island in astro_islands:
                    props_str = island.get('props', '')
                    if len(props_str) > 100:
                        # Look for name field in props
                        name_match = re.search(r'"name":\[0,"([^"]+)"', props_str)
                        if name_match:
                            manga_title = name_match.group(1).replace('\\u0026', '&')
                            break
                
                # Fallback: try from page title
                if manga_title in ["Unknown", "More..."] or len(manga_title) < 3:
                    title_tag = soup.find('title')
                    if title_tag:
                        title_text = title_tag.get_text()
                        # Remove " - Bato.to" or similar
                        manga_title = re.sub(r'\s*[-–|]\s*Bato.*$', '', title_text, flags=re.IGNORECASE).strip()
            
            # Extract chapters from the chapter list div
            chapter_list_div = soup.find('div', attrs={'name': 'chapter-list'})
            
            if not chapter_list_div:
                print("⚠️ No chapter list found!")
                return {
                    'manga_id': manga_id,
                    'manga_title': manga_title,
                    'total_chapters': 0,
                    'chapters': []
                }
            
            chapters = []
            
            # Find all chapter items (they're in <div> or <a> tags)
            # Structure: <a class="link-hover link-primary" href="/title/xxx/yyy">
            chapter_links = chapter_list_div.find_all('a', class_='link-primary', href=re.compile(r'/title/'))
            
            print(f"📖 Found {len(chapter_links)} chapter links, extracting details...")
            
            # Chapters are already in correct order on Bato (newest first)
            # We'll use the index as the order/position
            for idx, link in enumerate(chapter_links):
                try:
                    chapter_data = self._extract_chapter_data(link, soup, idx)
                    if chapter_data:
                        chapters.append(chapter_data)
                except Exception as e:
                    print(f"⚠️ Error extracting chapter {idx}: {e}")
                    continue
            
            # No need to sort - they're already in the correct order from the website!
            # Chapters are in website order (oldest to newest), so last one is the latest
            
            # Calculate stats
            latest_chapter = chapters[-1] if chapters else None
            
            result = {
                'manga_id': manga_id,
                'manga_title': manga_title,
                'total_chapters': len(chapters),
                'latest_chapter': {
                    'order': latest_chapter.get('chapter_order') if latest_chapter else None,
                    'title': latest_chapter.get('title') if latest_chapter else None,
                    'url': latest_chapter.get('url') if latest_chapter else None,
                    'uploaded_at': latest_chapter.get('uploaded_at') if latest_chapter else None
                } if latest_chapter else None,
                'chapters': chapters
            }
            
            print(f"✅ Extracted {len(chapters)} chapters!")
            if latest_chapter:
                print(f"   Latest: {latest_chapter.get('title')} (order: {latest_chapter.get('chapter_order')})")
                print(f"   Uploaded: {latest_chapter.get('uploaded_at')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error scraping chapters: {e}")
            await page.screenshot(path=f'error_chapters_{manga_id[:10]}.png')
            import traceback
            traceback.print_exc()
            raise
        finally:
            await page.close()
    
    def _extract_chapter_data(self, link_elem, soup: BeautifulSoup, idx: int) -> Dict:
        """Extract all data from a single chapter element."""
        
        # Basic info
        href = link_elem.get('href', '')
        full_url = f"https://batotwo.com{href}" if href.startswith('/') else href
        
        # Chapter title/name
        chapter_text = link_elem.get_text(strip=True)
        
        # Use index as chapter order, starting from 1 (for database compatibility)
        # This is simpler and more reliable than parsing chapter numbers
        chapter_order = idx + 1
        
        # Get parent div to extract additional info (date, group, etc.)
        parent_div = link_elem.find_parent('div', class_='flex')
        
        # Upload date - extract from <time> tag's "time" attribute
        uploaded_at = None
        uploaded_at_relative = None
        
        if parent_div:
            # Look for time element
            time_elem = parent_div.find('time')
            if time_elem:
                # Try 'time' attribute first (contains ISO datetime)
                time_attr = time_elem.get('time')
                if time_attr:
                    # Convert ISO datetime to MySQL format (YYYY-MM-DD HH:MM:SS)
                    try:
                        dt = datetime.fromisoformat(time_attr.replace('Z', '+00:00'))
                        uploaded_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        uploaded_at = time_attr
                else:
                    # Fallback to 'datetime' attribute
                    datetime_attr = time_elem.get('datetime')
                    if datetime_attr:
                        try:
                            dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                            uploaded_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            uploaded_at = datetime_attr
                
                # Get human-readable text
                uploaded_at_relative = time_elem.get_text(strip=True)
            
            # Fallback: look for text with time patterns (e.g., "2 days ago")
            if not uploaded_at_relative:
                time_pattern = re.compile(r'(\d+\s+(?:second|minute|hour|day|week|month|year)s?\s+ago)', re.IGNORECASE)
                time_match = parent_div.find(string=time_pattern)
                if time_match:
                    uploaded_at_relative = time_match.strip()
        
        # Removed: scanlation_group and language extraction (not needed)
        
        # Views/reads count
        views = None
        views_raw = None
        
        if parent_div:
            # Look for eye icon and count
            eye_icon = parent_div.find('i', attrs={'name': 'eye'})
            if eye_icon:
                views_span = eye_icon.find_next_sibling('span')
                if views_span:
                    views_text = views_span.get_text(strip=True)
                    views = views_text
                    # Try to parse raw number - handle formats like "905+4.6K"
                    try:
                        # Split by '+' and take the larger number
                        if '+' in views_text:
                            parts = views_text.split('+')
                            # Convert all parts and sum them
                            total = 0
                            for part in parts:
                                total += self._parse_number(part.strip())
                            views_raw = total
                        else:
                            views_raw = self._parse_number(views_text)
                    except:
                        pass
        
        # Removed: comments extraction (not needed)
        
        return {
            'chapter_order': chapter_order,
            'title': chapter_text,
            'url': full_url,
            'uploaded_at': uploaded_at,
            'views': views,
            'views_raw': views_raw
        }
    
    def _parse_number(self, text: str) -> int:
        """Parse formatted number (e.g., '1.5K' -> 1500)."""
        text = text.strip().upper()
        
        if 'M' in text:
            return int(float(text.replace('M', '')) * 1_000_000)
        elif 'K' in text:
            return int(float(text.replace('K', '')) * 1_000)
        else:
            return int(text)


async def main():
    """Test chapters list scraper."""
    async with BatoChaptersListScraper() as scraper:
        result = await scraper.scrape_chapters('110100-the-villainess-s-stationery-shop-official')
        
        # Save to JSON
        with open('chapters_list_output.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n� Saved to chapters_list_output.json")
        print(f"\n📊 Summary:")
        print(f"   Total chapters: {result['total_chapters']}")
        if result['latest_chapter']:
            print(f"   Latest: {result['latest_chapter']['title']} (order: {result['latest_chapter']['order']})")
        
        # Show first 3 chapters as sample
        print(f"\n📖 Sample chapters (first 3):")
        for ch in result['chapters'][:3]:
            print(f"   [{ch['chapter_order']}] {ch['title']}")
            print(f"      Uploaded: {ch['uploaded_at']}")
            print(f"      Views: {ch['views']}")

if __name__ == '__main__':
    asyncio.run(main())
