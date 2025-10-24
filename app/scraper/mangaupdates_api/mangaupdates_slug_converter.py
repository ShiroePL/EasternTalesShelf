"""
MangaUpdates API - Slug to ID Converter
Finding how to convert m9j8pqm → 48465726286
"""
import requests
import re
from bs4 import BeautifulSoup

def get_series_id_from_slug(slug):
    """
    Convert MangaUpdates slug (e.g., 'm9j8pqm') to numeric series ID.
    
    Multiple approaches:
    1. Search API
    2. Parse HTML page
    3. Check RSS feed URL
    """
    
    print(f"\n{'='*70}")
    print(f"Converting slug: {slug}")
    print(f"{'='*70}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
        'Accept': 'application/json',
    }
    
    # Method 1: Search API
    print("\n[Method 1] Using Search API...")
    try:
        search_url = "https://api.mangaupdates.com/v1/series/search"
        
        # Extract title from slug (not reliable but worth trying)
        # m9j8pqm doesn't tell us the title, so this won't work well
        
        print("  [SKIP] Can't extract title from slug")
        
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # Method 2: Parse HTML page
    print("\n[Method 2] Parsing HTML page...")
    try:
        page_url = f"https://www.mangaupdates.com/series/{slug}"
        print(f"  Fetching: {page_url}")
        
        response = requests.get(page_url, headers={'User-Agent': headers['User-Agent']}, timeout=10)
        html = response.text
        
        # Look for series ID in HTML
        # Check meta tags
        soup = BeautifulSoup(html, 'html.parser')
        
        # Method 2a: Look in meta tags
        og_url = soup.find('meta', property='og:url')
        if og_url:
            print(f"  Found og:url: {og_url.get('content')}")
        
        # Method 2b: Look for RSS feed link (contains numeric ID)
        rss_pattern = r'https://api\.mangaupdates\.com/v1/series/(\d+)/rss'
        rss_match = re.search(rss_pattern, html)
        
        if rss_match:
            series_id = rss_match.group(1)
            print(f"  [SUCCESS] Found series ID in RSS URL: {series_id}")
            return series_id
        
        # Method 2c: Look for series_id in JavaScript
        js_pattern = r'series_id["\s:]+(\d+)'
        js_match = re.search(js_pattern, html)
        
        if js_match:
            series_id = js_match.group(1)
            print(f"  [SUCCESS] Found series ID in JavaScript: {series_id}")
            return series_id
        
        # Method 2d: Look in Next.js props
        nextjs_pattern = r'"series_id":\s*(\d+)'
        nextjs_match = re.search(nextjs_pattern, html)
        
        if nextjs_match:
            series_id = nextjs_match.group(1)
            print(f"  [SUCCESS] Found series ID in Next.js props: {series_id}")
            return series_id
        
        print("  [FAIL] Could not find series ID in HTML")
        
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # Method 3: Try direct API calls with slug variations
    print("\n[Method 3] Trying API with slug...")
    try:
        api_url = f"https://api.mangaupdates.com/v1/series/{slug}"
        response = requests.get(api_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            series_id = data.get('series_id')
            print(f"  [SUCCESS] API accepts slug directly! ID: {series_id}")
            return series_id
        else:
            print(f"  [FAIL] Status: {response.status_code}")
            
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    return None

# Test it!
print("="*80)
print("MANGAUPDATES SLUG TO ID CONVERTER")
print("="*80)

test_slugs = [
    "5ojazp5"  # What Should I Do With My Brother?

]

results = {}

for slug in test_slugs:
    series_id = get_series_id_from_slug(slug)
    if series_id:
        results[slug] = series_id
        print(f"\n[RESULT] {slug} → {series_id}")
        
        # Verify by calling API
        api_url = f"https://api.mangaupdates.com/v1/series/{series_id}"
        try:
            response = requests.get(api_url, headers={'Accept': 'application/json'}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"[VERIFY] ✓ Title: {data.get('title')}")
            else:
                print(f"[VERIFY] ✗ Failed with status {response.status_code}")
        except Exception as e:
            print(f"[VERIFY] ✗ {e}")
    else:
        print(f"\n[RESULT] {slug} → FAILED")

print("\n" + "="*80)
print(f"CONVERSION COMPLETE: {len(results)}/{len(test_slugs)} successful")
print("="*80)

if results:
    print("\nSummary:")
    for slug, series_id in results.items():
        print(f"  {slug} → {series_id}")
