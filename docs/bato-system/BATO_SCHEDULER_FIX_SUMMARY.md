# Bato Scheduler Fix Summary

## Problem Identified

The bato scheduling system was creating extreme scheduling intervals (30+ days) for manga that hadn't been updated in a long time. 

### Root Causes

Based on your data analysis:

1. **No-update Penalty Stacking**: The system applies a 1.5x multiplier for each consecutive scrape with no new chapters (up to 3 times). This created intervals like:
   - 1 no-update: 24h × 1.5 = 36h
   - 2 no-updates: 24h × 2.25 = 54h  
   - 3 no-updates: 24h × 3.375 = 81h

2. **Large Base Intervals**: When manga had very long gaps between old chapters, the pattern analyzer would calculate a large average interval. The penalty would then multiply this already-large interval.

3. **Completed/Dropped Status**: Manga marked as 'completed' or 'dropped' automatically got 30-day intervals, which was correct per requirements but didn't account for potential re-activation.

4. **No Time-Awareness**: The system didn't consider HOW LONG it had been since the last chapter. A manga with a chapter 522 days ago was treated the same as one with a chapter 5 days ago.

### Example Issues from Your Data

| Manga | Last Chapter | Next Scrape | Issue |
|-------|--------------|-------------|-------|
| Run Meil (ID 9) | 522 days ago | 30 days out | Likely marked completed/dropped |
| Evil Princess (ID 7) | 296 days ago | 7 days out | Too optimistic for inactive manga |
| My Farm (ID 8) | 12 days ago | 9+ days out | Reasonable but could be better |
| Sistervention (ID 10) | 2 days ago | 4 days out | Good for active manga |

## Solutions Implemented

### 1. **Time-Since-Last-Chapter Awareness**

Added new method `_get_days_since_last_chapter()` that calculates how long it's been since a manga last released a chapter. This provides context for scheduling decisions.

### 2. **Smart Inactivity Adjustment**

Added new method `_adjust_for_inactivity()` that implements tiered scheduling based on inactivity:

```python
# Recently active (<30 days): No adjustment, check based on pattern
# Moderately inactive (30-90 days): Check weekly (7 days)
# Very inactive (90-180 days): Check bi-weekly (14 days)  
# Likely abandoned (>180 days): Check every 3 weeks (21 days)
```

This ensures:
- Active manga get checked frequently
- Inactive manga don't get abandoned completely
- Server resources aren't wasted on dead manga

### 3. **Absolute Maximum Interval Cap**

Added `ABSOLUTE_MAX_INTERVAL_DAYS = 21` constant that caps ALL intervals at 3 weeks, even with penalties applied. This prevents the extreme 30+ day schedules.

### 4. **Smarter No-Update Penalty**

Modified `_apply_no_update_penalty()` to:
- Only apply to short-to-medium intervals (<7 days)
- Skip penalty if interval is already long
- Work in conjunction with inactivity adjustment (not redundantly)

### 5. **Enhanced Logging**

Added comprehensive logging that shows:
- Days since last chapter release
- Which adjustments were applied
- Final interval in both hours and days
- Reasoning behind scheduling decisions

Example log output:
```
Calculated next scrape: anilist_id 12345: next_scrape=2025-11-10 15:30, 
interval=168.0h (7.0 days), days_since_last_chapter=45.2, no_updates=2
```

## New Scheduling Behavior

### For Your Example Manga:

**Run Meil (522 days since last chapter)**:
- Before: 30 days (completed/dropped status)
- After: 21 days (abandoned check, absolute max cap)
- Reasoning: Hasn't updated in 1.5 years, but we'll still check occasionally

**Evil Princess (296 days since last chapter)**:
- Before: 7 days  
- After: 21 days (abandoned check)
- Reasoning: Likely abandoned, reduced checking frequency

**My Farm (12 days since last chapter)**:
- Before: 9 days
- After: ~24-48 hours (recently active)
- Reasoning: Recent activity suggests ongoing releases, check frequently

**Sistervention (2 days since last chapter)**:
- Before: 4 days
- After: ~24-48 hours (very recently active)  
- Reasoning: Very recent activity, check soon

## Benefits

1. **Resource Efficiency**: Reduces unnecessary scraping of inactive manga
2. **Responsiveness**: Keeps checking active manga frequently
3. **No Abandonment**: Even very old manga get checked every 3 weeks
4. **Prevents Extremes**: Absolute cap prevents 30+ day schedules
5. **Better Logging**: Easy to debug and understand scheduling decisions
6. **Adaptability**: System adjusts as manga becomes active/inactive

## Testing Recommendations

1. **Monitor logs** after deployment to see the new scheduling decisions
2. **Check manga with different inactivity levels**:
   - Very active (daily releases)
   - Moderately active (weekly releases)
   - Inactive (no chapters in months)
   - Completed/dropped status

3. **Verify the absolute max cap** is working:
```sql
SELECT anilist_id, bato_link, 
       TIMESTAMPDIFF(DAY, NOW(), next_scrape_at) as days_until_next
FROM bato_scraping_schedule
WHERE days_until_next > 21;
```

4. **Check that recently active manga** get short intervals:
```sql
SELECT s.anilist_id, m.name,
       TIMESTAMPDIFF(DAY, MAX(c.date_public), NOW()) as days_since_last,
       s.scraping_interval_hours / 24 as interval_days
FROM bato_scraping_schedule s
JOIN bato_manga_details m ON s.anilist_id = m.anilist_id
LEFT JOIN bato_chapters c ON s.anilist_id = c.anilist_id
GROUP BY s.anilist_id
HAVING days_since_last < 30
ORDER BY days_since_last;
```

## Configuration

All constants are configurable in `scheduling_engine.py`:

```python
DEFAULT_INTERVAL_HOURS = 24          # Initial interval for new manga
MIN_INTERVAL_HOURS = 6              # Minimum scraping interval  
MAX_INTERVAL_DAYS = 14              # Maximum from original requirements
ABSOLUTE_MAX_INTERVAL_DAYS = 21     # NEW: Absolute cap with penalties

DAYS_INACTIVE_SHORT = 30            # Recently active threshold
DAYS_INACTIVE_MEDIUM = 90           # Moderately inactive threshold  
DAYS_INACTIVE_LONG = 180            # Very inactive threshold
```

Adjust these values based on your server capacity and scraping needs.

## Migration Path

For existing schedules with extreme intervals:

```sql
-- Reset extreme schedules to reasonable values
UPDATE bato_scraping_schedule
SET next_scrape_at = DATE_ADD(NOW(), INTERVAL 7 DAY),
    consecutive_no_update_count = 0
WHERE TIMESTAMPDIFF(DAY, NOW(), next_scrape_at) > 21;
```

This will give the new system a clean slate for recalculating schedules.
