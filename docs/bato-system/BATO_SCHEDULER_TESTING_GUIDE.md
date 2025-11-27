# Quick Start Guide for Testing Bato Scheduler Fixes

## What Changed

The bato scheduler now intelligently adjusts scraping intervals based on how long it's been since a manga's last chapter release. This prevents over-scheduling inactive manga while keeping active manga checked frequently.

## Step-by-Step Testing

### 1. Analyze Current State

Run the analysis queries to see current scheduling problems:

```bash
# Connect to your database
mysql -u your_user -p anilist_database

# Or if using SQLite
sqlite3 your_database.db
```

Run queries from `bato_scheduler_analysis.sql`:
- Query #1: Shows manga with extreme intervals (>21 days)
- Query #2: Shows distribution of intervals
- Query #3: Shows manga by activity level
- Query #4: Shows your specific problematic manga

### 2. Optional: Reset Schedules

If you want to start fresh, uncomment and run one of these in `bato_scheduler_analysis.sql`:

**Option A - Conservative** (Recommended first):
```sql
-- Reset only extreme schedules (>21 days) to 7 days
UPDATE bato_scraping_schedule
SET next_scrape_at = DATE_ADD(NOW(), INTERVAL 7 DAY),
    consecutive_no_update_count = 0
WHERE TIMESTAMPDIFF(DAY, NOW(), next_scrape_at) > 21;
```

**Option B - Aggressive**:
```sql
-- Reset your 5 specific manga for immediate testing
UPDATE bato_scraping_schedule
SET next_scrape_at = NOW(),
    consecutive_no_update_count = 0
WHERE anilist_id IN (135109, 150106, 155461, 170154, 138363);
```

### 3. Restart the Bato Service

The changes are in the scheduler engine, so restart your container:

```bash
# If using Docker
docker-compose restart bato_service

# Or if running standalone
# Stop the current process and restart it
```

### 4. Watch the Logs

Monitor the enhanced logging to see the new scheduling decisions:

```bash
# Docker logs
docker-compose logs -f bato_service

# Or check the log files
tail -f logs/bato/bato_service.log
```

Look for log entries like:
```
INFO: Calculated next scrape: anilist_id 135109: next_scrape=2025-11-10 15:30, 
      interval=504.0h (21.0 days), days_since_last_chapter=296.3
```

### 5. Verify New Behavior

After a few scrapes, run the monitoring queries:

**Check that active manga get short intervals:**
```sql
SELECT s.anilist_id, m.name,
       TIMESTAMPDIFF(DAY, MAX(c.date_public), NOW()) as days_since_last,
       s.scraping_interval_hours / 24 as interval_days,
       s.next_scrape_at
FROM bato_scraping_schedule s
JOIN bato_manga_details m ON s.anilist_id = m.anilist_id
LEFT JOIN bato_chapters c ON s.anilist_id = c.anilist_id
GROUP BY s.anilist_id
HAVING days_since_last < 30
ORDER BY days_since_last;
```

**Check that inactive manga get long intervals:**
```sql
SELECT s.anilist_id, m.name,
       TIMESTAMPDIFF(DAY, MAX(c.date_public), NOW()) as days_since_last,
       s.scraping_interval_hours / 24 as interval_days,
       s.next_scrape_at
FROM bato_scraping_schedule s
JOIN bato_manga_details m ON s.anilist_id = m.anilist_id
LEFT JOIN bato_chapters c ON s.anilist_id = c.anilist_id
GROUP BY s.anilist_id
HAVING days_since_last > 180
ORDER BY days_since_last DESC;
```

**Verify no extreme schedules:**
```sql
SELECT COUNT(*) as extreme_schedules
FROM bato_scraping_schedule
WHERE TIMESTAMPDIFF(DAY, NOW(), next_scrape_at) > 21;
```

Should return 0 (or very few for completed/dropped manga).

### 6. Expected Behavior

Based on your example manga:

| Manga | Days Since Last | Expected Interval | Reason |
|-------|----------------|-------------------|---------|
| Sistervention | 2 days | 1-2 days | Very active, check soon |
| My Farm | 12 days | 1-2 days | Recently active |
| Evil Princess | 296 days | 21 days | Likely abandoned, but keep checking |
| Run Meil | 522 days | 21 days | Very old, max interval cap |
| Male Lead's Lion | Never scraped | 24 hours | New manga, default interval |

### 7. Fine-Tuning (Optional)

If you want to adjust the thresholds, edit `app/services/bato/scheduling_engine.py`:

```python
# Time-based thresholds for inactive manga handling
DAYS_INACTIVE_SHORT = 30      # Less than 30 days = recently active
DAYS_INACTIVE_MEDIUM = 90     # 30-90 days = moderately inactive  
DAYS_INACTIVE_LONG = 180      # 90-180 days = very inactive
# Over 180 days = likely abandoned

# Max interval even with penalties
ABSOLUTE_MAX_INTERVAL_DAYS = 21  # Never schedule more than 3 weeks out
```

Adjust these based on:
- Your server capacity (more capacity = shorter intervals)
- Manga update frequency in your collection
- How important it is to catch new chapters quickly

### 8. Monitoring Dashboard

Add these queries to your admin dashboard:

**Scraping Schedule Health:**
```sql
SELECT 
    'Total Active' as metric,
    COUNT(*) as value
FROM bato_scraping_schedule WHERE is_active = 1
UNION ALL
SELECT 
    'Due Now' as metric,
    COUNT(*) as value
FROM bato_scraping_schedule 
WHERE next_scrape_at <= NOW() AND is_active = 1
UNION ALL
SELECT 
    'Due Today' as metric,
    COUNT(*) as value
FROM bato_scraping_schedule 
WHERE DATE(next_scrape_at) = CURDATE() AND is_active = 1
UNION ALL
SELECT 
    'Extreme Intervals (>21d)' as metric,
    COUNT(*) as value
FROM bato_scraping_schedule 
WHERE TIMESTAMPDIFF(DAY, NOW(), next_scrape_at) > 21;
```

## Troubleshooting

### Problem: Manga still getting 30-day schedules

**Check upload_status:**
```sql
SELECT anilist_id, name, upload_status 
FROM bato_manga_details 
WHERE upload_status IN ('completed', 'dropped');
```

Completed/dropped manga intentionally get 30-day intervals. If this is wrong, update the status:
```sql
UPDATE bato_manga_details 
SET upload_status = 'ongoing' 
WHERE anilist_id = 155461;  -- Run Meil example
```

### Problem: Active manga getting long intervals

Check the logs for that specific manga. Look for:
- Days since last chapter (should be low for active)
- Whether inactivity adjustment was applied
- Pattern detection results

### Problem: Too many manga scraping at once

The system processes sequentially with 4-7 second delays between manga. If you have many manga due at once:

1. Spread them out:
```sql
UPDATE bato_scraping_schedule
SET next_scrape_at = DATE_ADD(NOW(), 
    INTERVAL FLOOR(RAND() * 168) HOUR)  -- Random within next week
WHERE is_active = 1;
```

2. Or adjust the delay in `bato_scraping_service.py`:
```python
MIN_DELAY_BETWEEN_SCRAPES = 2.0  # Reduce from 4.0
MAX_DELAY_BETWEEN_SCRAPES = 4.0  # Reduce from 7.0
```

## Success Criteria

After running for 24-48 hours, you should see:

✅ No schedules >21 days out (except intentional completed/dropped)  
✅ Active manga (<30 days since last chapter) checked within 1-3 days  
✅ Inactive manga (>180 days) checked every 2-3 weeks  
✅ Logs showing "days_since_last_chapter" in schedule calculations  
✅ No "MySQL server has gone away" errors  
✅ Successful scrape rate >90%  

## Questions or Issues?

Check the logs first:
```bash
tail -f logs/bato/bato_service.log | grep -E "Calculated next scrape|days_since_last"
```

The enhanced logging will show you exactly why each scheduling decision was made.
