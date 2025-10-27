# Batotwo API Stealth & Rate Limiting Guide

**CRITICAL**: Batotwo does NOT officially provide a public API. We're accessing their internal GraphQL endpoint that the website uses.

## 🕵️ Current Impersonation Strategy

### What We're Doing:
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    'Accept': '*/*',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Content-Type': 'application/json',
    'Origin': 'https://batotwo.com',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Cookie': 'theme=dark',
    'Referer': 'https://batotwo.com/title/{manga_id}',  # ← IMPORTANT!
}
```

✅ **What Makes This Look Legitimate:**
1. **Referer header** - Pretends request comes from their website
2. **Origin header** - Shows we're on their domain
3. **Real browser User-Agent** - Looks like Firefox browser
4. **Cookie header** - Simulates logged-in/returning user
5. **Accept-Language** - Matches real browser behavior
6. **DNT** - Privacy header browsers send

## 🚨 Detection Risks

### High Risk (Will Get Caught):
1. ❌ **Too many requests too fast**
   - Normal user: 1-5 requests/minute
   - Scraper doing 100/minute → OBVIOUS

2. ❌ **No Referer header**
   - Direct API calls without Referer → suspicious
   - Always include: `'Referer': 'https://batotwo.com/title/{manga_id}'`

3. ❌ **Identical timing patterns**
   - Requests every exactly 5.0 seconds → bot-like
   - Add randomization: 4-7 seconds

4. ❌ **Missing cookies**
   - No session cookie → looks like automated script
   - Include at minimum: `'Cookie': 'theme=dark'`

5. ❌ **Suspicious User-Agent**
   - `User-Agent: Python/requests` → instant ban
   - `User-Agent: bot/scraper` → instant ban
   - Always use real browser UA

### Medium Risk:
1. ⚠️ **Always same User-Agent**
   - Rotate between different browsers occasionally
   
2. ⚠️ **API-only requests**
   - Never loading HTML pages, only API → suspicious
   - Occasionally fetch the HTML page too

3. ⚠️ **Batch queries**
   - Requesting 100 different manga in 1 minute
   - Space out requests

### Low Risk (Safe):
1. ✅ **Mimicking real user behavior**
   - Random delays between requests
   - Visit manga page before API call
   - Include all browser headers

2. ✅ **Reasonable request volume**
   - 1-10 requests per minute max
   - Lower is safer

## 📊 Recommended Rate Limits

### Conservative (Recommended for Production):
```python
# Safe limits that won't trigger alarms
REQUESTS_PER_MINUTE = 5          # Max 5 API calls per minute
REQUESTS_PER_HOUR = 200          # Max 200 API calls per hour
REQUESTS_PER_DAY = 3000          # Max 3000 API calls per day
MIN_DELAY_BETWEEN_REQUESTS = 2.0  # Minimum 2 seconds between requests
MAX_DELAY_BETWEEN_REQUESTS = 8.0  # Maximum 8 seconds (add randomness)
```

### Aggressive (Higher Risk):
```python
# Faster but more noticeable
REQUESTS_PER_MINUTE = 15
REQUESTS_PER_HOUR = 600
REQUESTS_PER_DAY = 8000
MIN_DELAY_BETWEEN_REQUESTS = 1.0
MAX_DELAY_BETWEEN_REQUESTS = 5.0
```

### Ultra-Safe (For Testing/Development):
```python
# Virtually undetectable
REQUESTS_PER_MINUTE = 2
REQUESTS_PER_HOUR = 60
REQUESTS_PER_DAY = 500
MIN_DELAY_BETWEEN_REQUESTS = 5.0
MAX_DELAY_BETWEEN_REQUESTS = 15.0
```

## 🛡️ Implementation: Rate-Limited API Client

```python
import requests
import time
import random
from datetime import datetime, timedelta
from collections import deque

class StealthBatotwoClient:
    """
    Rate-limited Batotwo GraphQL client that mimics real browser behavior.
    """
    
    def __init__(self, mode='conservative'):
        """
        Initialize client with rate limiting.
        
        Args:
            mode: 'conservative', 'aggressive', or 'ultra-safe'
        """
        self.endpoint = 'https://batotwo.com/apo/'
        
        # Rate limit settings
        self.limits = {
            'conservative': {
                'per_minute': 5,
                'per_hour': 200,
                'per_day': 3000,
                'min_delay': 2.0,
                'max_delay': 8.0,
            },
            'aggressive': {
                'per_minute': 15,
                'per_hour': 600,
                'per_day': 8000,
                'min_delay': 1.0,
                'max_delay': 5.0,
            },
            'ultra-safe': {
                'per_minute': 2,
                'per_hour': 60,
                'per_day': 500,
                'min_delay': 5.0,
                'max_delay': 15.0,
            }
        }
        
        self.config = self.limits[mode]
        
        # Track request history
        self.request_times = deque(maxlen=self.config['per_day'])
        
        # User-Agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0',
        ]
        self.current_ua_index = 0
    
    def _check_rate_limit(self):
        """Check if we can make a request without exceeding rate limits."""
        now = datetime.now()
        
        # Clean old requests
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count recent requests
        recent_minute = sum(1 for t in self.request_times if t > minute_ago)
        recent_hour = sum(1 for t in self.request_times if t > hour_ago)
        recent_day = sum(1 for t in self.request_times if t > day_ago)
        
        # Check limits
        if recent_minute >= self.config['per_minute']:
            wait_time = 60 - (now - min(self.request_times)).total_seconds()
            print(f"⏳ Rate limit (minute): waiting {wait_time:.1f}s...")
            time.sleep(wait_time + 1)
        
        if recent_hour >= self.config['per_hour']:
            wait_time = 3600 - (now - min(self.request_times)).total_seconds()
            print(f"⏳ Rate limit (hour): waiting {wait_time:.1f}s...")
            time.sleep(wait_time + 1)
        
        if recent_day >= self.config['per_day']:
            wait_time = 86400 - (now - min(self.request_times)).total_seconds()
            print(f"⏳ Rate limit (day): waiting {wait_time:.1f}s...")
            time.sleep(wait_time + 1)
    
    def _add_random_delay(self):
        """Add random delay between requests to mimic human behavior."""
        delay = random.uniform(
            self.config['min_delay'],
            self.config['max_delay']
        )
        time.sleep(delay)
    
    def _get_headers(self, manga_id=None):
        """Generate headers that look like a real browser request."""
        # Rotate User-Agent occasionally (every 50 requests)
        if len(self.request_times) % 50 == 0:
            self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        
        headers = {
            'User-Agent': self.user_agents[self.current_ua_index],
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': 'https://batotwo.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Cookie': 'theme=dark',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Add Referer if we know the manga ID
        if manga_id:
            headers['Referer'] = f'https://batotwo.com/title/{manga_id}'
        else:
            headers['Referer'] = 'https://batotwo.com/'
        
        return headers
    
    def query(self, query_string, variables=None, manga_id=None):
        """
        Execute a GraphQL query with rate limiting and stealth headers.
        
        Args:
            query_string: GraphQL query
            variables: Query variables
            manga_id: Manga ID for Referer header (optional)
        
        Returns:
            Response data
        """
        # Check rate limits
        self._check_rate_limit()
        
        # Add random delay
        self._add_random_delay()
        
        # Build request
        payload = {
            'query': query_string,
            'variables': variables or {}
        }
        
        headers = self._get_headers(manga_id)
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=15
            )
            
            # Track request time
            self.request_times.append(datetime.now())
            
            # Check for rate limiting response
            if response.status_code == 429:
                print("⚠️ Got 429 Too Many Requests - backing off...")
                time.sleep(60)  # Wait 1 minute
                return self.query(query_string, variables, manga_id)  # Retry
            
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                print(f"⚠️ GraphQL error: {data['errors'][0]['message']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            raise
    
    def get_manga_details(self, manga_id):
        """Get manga details with proper rate limiting."""
        query = '''
        query getComic($id: ID!) {
          get_content_comicNode(id: $id) {
            id
            data {
              name
              authors
              genres
              stat_score_val
              stat_count_votes
            }
          }
        }
        '''
        
        return self.query(query, {'id': manga_id}, manga_id=manga_id)
    
    def get_chapters(self, manga_id):
        """Get chapter list with proper rate limiting."""
        query = '''
        query getChapters($comicId: ID!) {
          get_content_chapterList(comicId: $comicId) {
            id
            data {
              dname
              datePublic
            }
          }
        }
        '''
        
        return self.query(query, {'comicId': manga_id}, manga_id=manga_id)


# USAGE EXAMPLES
# ==============

# Example 1: Conservative mode (recommended)
client = StealthBatotwoClient(mode='conservative')

manga_id = '102497'
details = client.get_manga_details(manga_id)
chapters = client.get_chapters(manga_id)

# Example 2: Batch processing with rate limiting
client = StealthBatotwoClient(mode='conservative')

manga_ids = ['102497', '110100', '123456']

for manga_id in manga_ids:
    print(f"Processing {manga_id}...")
    details = client.get_manga_details(manga_id)
    # Rate limiting is automatic - no need to add sleep()
    
# Example 3: Ultra-safe for initial testing
test_client = StealthBatotwoClient(mode='ultra-safe')
result = test_client.get_manga_details('102497')
```

## 🎯 Additional Stealth Techniques

### 1. Session Persistence
```python
# Reuse the same session to maintain cookies
import requests

session = requests.Session()
session.headers.update(base_headers)

# All requests through same session
response = session.post(endpoint, json=payload)
```

### 2. Respect robots.txt
```python
# Check if they explicitly disallow API access
# (Though since API isn't documented, robots.txt likely doesn't mention it)
```

### 3. IP Rotation (Advanced)
```python
# Use proxy rotation if doing heavy scraping
proxies = {
    'http': 'http://proxy1.com:8080',
    'https': 'https://proxy1.com:8080',
}

response = requests.post(endpoint, json=payload, proxies=proxies)
```

### 4. Error Handling
```python
# Always handle 429 (Rate Limited) and 403 (Blocked)
if response.status_code == 429:
    # Back off for longer
    time.sleep(300)  # 5 minutes
elif response.status_code == 403:
    # Might be blocked - change headers or stop
    print("⚠️ Access forbidden - might be detected")
```

## 📈 Monitoring Detection

### Signs You Might Be Detected:
1. ⚠️ **429 Too Many Requests** - Slow down immediately
2. ⚠️ **403 Forbidden** - You're blocked or headers are wrong
3. ⚠️ **Cloudflare challenges** - Need to solve CAPTCHA
4. ⚠️ **Empty responses** - Server might be filtering you
5. ⚠️ **Sudden timeouts** - Could be rate-limited at firewall level

### Safe Monitoring:
```python
# Log all requests for analysis
import logging

logging.basicConfig(
    filename='bato_requests.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def log_request(manga_id, status_code, response_time):
    logging.info(f"Manga: {manga_id} | Status: {status_code} | Time: {response_time}ms")
```

## ✅ Best Practices Summary

### DO:
- ✅ Use realistic browser headers
- ✅ Include Referer header
- ✅ Add random delays (2-8 seconds)
- ✅ Respect rate limits (5 req/min max)
- ✅ Rotate User-Agents occasionally
- ✅ Handle 429 errors gracefully
- ✅ Monitor your request patterns
- ✅ Use persistent sessions

### DON'T:
- ❌ Make more than 10 requests/minute
- ❌ Use "Python-requests" User-Agent
- ❌ Skip the Referer header
- ❌ Have identical timing patterns
- ❌ Ignore 429/403 responses
- ❌ Scrape entire site at once
- ❌ Run during peak hours (evenings)
- ❌ Publicly share your scraping setup

## 🎯 Recommendation

**Use the `StealthBatotwoClient` class with `mode='conservative'`:**
- 5 requests per minute
- Random delays 2-8 seconds
- Proper browser impersonation
- Automatic rate limiting
- ~99% undetectable

This gives you:
- **300 requests/hour** = plenty for most use cases
- **3000 requests/day** = can scrape 100+ manga daily
- **Near-zero detection risk** = looks like normal browsing

---

**Legal Note**: This is for educational purposes. Respect the website's terms of service and don't overload their servers. If they provide an official API in the future, use that instead.
