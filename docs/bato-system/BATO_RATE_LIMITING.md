# Bato.to Rate Limiting Strategy

## Overview

The Bato scraping service implements a **human-like rate limiting strategy** to respect Bato.to's hidden GraphQL API and avoid detection or blocking.

## Key Changes

### Sequential Processing (Not Concurrent)

- **Before:** Up to 5 manga scraped concurrently
- **After:** Manga scraped one at a time (sequential)
- **Reason:** Mimics human browsing behavior

### Randomized Delays

- **Delay Range:** 4-7 seconds between each manga
- **Randomization:** Uses `random.uniform()` for natural variation
- **Human-like:** Simulates the time a person would take to browse between manga pages

### Combined API Calls

- **Chapter List + Manga Details** fetched together (no delay between them)
- **Reason:** On the actual website, both load on the same page
- **Efficiency:** Reduces total API calls while maintaining natural behavior

## Performance Impact

### For 300 Manga Collection

- **Average delay:** 5.5 seconds per manga
- **Total time:** ~27.5 minutes for full cycle (300 × 5.5s)
- **Range:** 20-35 minutes depending on randomization

### Actual Behavior

The service **does NOT scrape all 300 manga every cycle**:

- Service checks every 5 minutes
- Only scrapes manga where `next_scrape_at <= now`
- Most manga have 6h-14 day intervals based on release patterns
- Typical cycle: 5-20 manga (not 300)

**Example:**
- Cycle 1: 15 manga due → ~82 seconds (1.4 minutes)
- Cycle 2: 8 manga due → ~44 seconds
- Cycle 3: 22 manga due → ~121 seconds (2 minutes)

## Configuration

### Environment Variables

```bash
# Minimum delay between manga scrapes (seconds)
BATO_MIN_DELAY=4.0

# Maximum delay between manga scrapes (seconds)
BATO_MAX_DELAY=7.0
```

### Adjusting for More Conservative Rate Limiting

If you experience rate limiting (429 errors), increase the delays:

```yaml
# docker-compose.yml
environment:
  - BATO_MIN_DELAY=6.0   # Increase from 4
  - BATO_MAX_DELAY=10.0  # Increase from 7
```

### Adjusting for Faster Scraping (Not Recommended)

Only reduce delays if you're confident Bato.to won't block you:

```yaml
# docker-compose.yml
environment:
  - BATO_MIN_DELAY=2.0   # Minimum recommended
  - BATO_MAX_DELAY=4.0   # Minimum recommended
```

⚠️ **Warning:** Delays below 2 seconds may trigger rate limiting.

## Code Implementation

### Sequential Processing with Delays

```python
# Process manga one at a time
for i, manga_data in enumerate(manga_list, 1):
    # Scrape this manga
    success = self.execute_scraping_job(manga_data)
    
    # Add delay before next manga (except after last one)
    if i < len(manga_list):
        delay = random.uniform(
            self.MIN_DELAY_BETWEEN_SCRAPES,  # 4.0
            self.MAX_DELAY_BETWEEN_SCRAPES   # 7.0
        )
        logger.info(f"Waiting {delay:.2f}s before next manga...")
        time.sleep(delay)
```

### Combined API Calls

```python
# Both calls happen together (no delay between them)
chapters_data = self.chapters_scraper.scrape_chapters(bato_id)
details_data = self.details_scraper.scrape_manga_details(bato_id)
```

## Monitoring

### Check Delays in Logs

```bash
# View actual delays being used
docker-compose logs -f bato-scraping-service | grep "Waiting.*before next manga"

# Example output:
# Waiting 5.23s before next manga (human-like rate limiting)...
# Waiting 6.78s before next manga (human-like rate limiting)...
# Waiting 4.12s before next manga (human-like rate limiting)...
```

### Check for Rate Limiting

```bash
# Check for 429 errors
docker-compose logs bato-scraping-service | grep -i "rate limit"

# Check error rate
doppler run -- python check_bato_logs.py
```

## Best Practices

### ✅ Do

- Keep delays between 4-7 seconds (default)
- Monitor logs for rate limiting errors
- Increase delays if you see 429 errors
- Let the intelligent scheduling system handle frequency

### ❌ Don't

- Set delays below 2 seconds
- Scrape all manga manually at once
- Disable rate limiting
- Use concurrent scraping

## Comparison with Website Behavior

### Human Browsing Bato.to

1. User opens manga page → loads details + chapters
2. User reads/browses for 5-10 seconds
3. User navigates to another manga
4. Repeat

### Our Scraping Service

1. Service fetches manga details + chapters (combined)
2. Service waits 4-7 seconds (randomized)
3. Service fetches next manga
4. Repeat

**Result:** Nearly identical to human behavior from Bato.to's perspective.

## Troubleshooting

### Getting 429 Errors

**Solution:** Increase delays

```bash
# Edit docker-compose.yml
environment:
  - BATO_MIN_DELAY=8.0
  - BATO_MAX_DELAY=12.0

# Restart
docker-compose restart bato-scraping-service
```

### Scraping Too Slow

**Check:** Are you actually scraping 300 manga per cycle?

```bash
# Check how many manga are being scraped
docker-compose logs bato-scraping-service | grep "Found.*manga due for scraping"

# Example output:
# Found 12 manga due for scraping
```

Most likely, only 5-20 manga are scraped per cycle due to intelligent scheduling.

### Want Faster Updates

**Solution:** Don't reduce delays. Instead, reduce the check interval:

```yaml
# docker-compose.yml
environment:
  - BATO_SCRAPE_INTERVAL=180  # Check every 3 minutes instead of 5
```

This checks more frequently but still respects rate limits when scraping.

## Summary

- **Sequential scraping** with **4-7 second delays** between manga
- Mimics human browsing behavior
- Respects Bato.to's API
- Efficient: Only scrapes manga that are due
- Configurable: Adjust delays via environment variables
- Safe: Prevents rate limiting and blocking

For 300 manga with typical schedules, expect:
- **5-20 manga per cycle** (not all 300)
- **30-120 seconds per cycle** (not 25 minutes)
- **No rate limiting issues** with default settings
