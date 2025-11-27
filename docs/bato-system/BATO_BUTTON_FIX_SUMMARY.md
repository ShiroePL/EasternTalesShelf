# Bato "Add Link" Button - Bug Fix Summary

**Date:** October 24, 2025  
**Issue:** New manga added via "Add Bato Link" button failed to save any data to Bato tables

---

## 🐛 The Problem

When clicking "Add Bato Link" button for a new manga, the following errors occurred:

### 1. Manga Details Insert Failed
```
ERROR - Error upserting manga details: Unconsumed column names: rating_value, views, rating_count, is_licensed
```

**Cause:** Code used wrong column names that don't exist in database schema.

### 2. All Chapters Insert Failed (59/59 failures)
```
WARNING - Error inserting chapter: 'view_count' is an invalid keyword argument for BatoChapters
```

**Cause:** Code used `view_count` instead of correct `stat_count_*` columns.

### 3. Schedule Insert Failed
```
ERROR - Error upserting schedule: 'scrape_interval_hours' is an invalid keyword argument for BatoScrapingSchedule
```

**Cause:** Code used `scrape_interval_hours` instead of correct `scraping_interval_hours`.

### 4. Log Insert Failed
```
ERROR - Cannot add or update a child row: a foreign key constraint fails
```

**Cause:** Log entry tried to reference `bato_manga_details` that was never inserted (failed in step 1).

### Result
```
✅ 0 manga details saved
✅ 0 chapters saved  
✅ 0 schedules created
❌ Manga invisible to Bato container
❌ No notifications ever generated
```

---

## ✅ The Fix

### Changed Files: 1
- `app/blueprints/manga.py`

### Changes Made

#### 1. Fixed Manga Details Column Names

**Before (WRONG):**
```python
manga_details_dict = {
    'alt_names': ','.join(...),  # ❌ Should be JSON, not comma-separated
    'authors': ','.join(...),    # ❌ Should be JSON
    'artists': ','.join(...),    # ❌ Should be JSON
    'genres': ','.join(...),     # ❌ Should be JSON
    'views': ...,                # ❌ Column doesn't exist
    'rating_value': ...,         # ❌ Column doesn't exist
    'rating_count': ...,         # ❌ Column doesn't exist
    'is_licensed': ...           # ❌ Column doesn't exist
}
```

**After (CORRECT):**
```python
manga_details_dict = {
    'alt_names': details_data.get('alt_names', []),  # ✅ JSON array
    'authors': details_data.get('authors', []),      # ✅ JSON array
    'artists': details_data.get('artists', []),      # ✅ JSON array
    'genres': details_data.get('genres', []),        # ✅ JSON array
    # Rating data (stat_score_*)
    'stat_score_val': details_data.get('stat_score_val', 0.0),
    'stat_count_votes': details_data.get('stat_count_votes', 0),
    'stat_count_scores': details_data.get('stat_count_scores', []),
    # Statistics (stat_count_*)
    'stat_count_follows': details_data.get('stat_count_follows', 0),
    'stat_count_reviews': details_data.get('stat_count_reviews', 0),
    'stat_count_post_reply': details_data.get('stat_count_post_reply', 0),
    'stat_count_views_total': details_data.get('stat_count_views_total', 0),
    'stat_count_emotions': details_data.get('stat_count_emotions', []),
    # ... (see bato_models.py for all columns)
}
```

#### 2. Fixed Chapter Column Names

**Before (WRONG):**
```python
chapter_dict = {
    'view_count': chapter.get('view_count', 0)  # ❌ Column doesn't exist
}
```

**After (CORRECT):**
```python
chapter_dict = {
    'canonical_chapter_id': chapter.get('canonical_chapter_id'),  # ✅ Required field
    # Statistics (stat_count_*)
    'stat_count_views_guest': chapter.get('stat_count_views_guest', 0),
    'stat_count_views_login': chapter.get('stat_count_views_login', 0),
    'stat_count_views_total': chapter.get('stat_count_views_total', 0),
    'stat_count_post_reply': chapter.get('stat_count_post_reply', 0)
}
```

#### 3. Fixed Schedule Column Name

**Before (WRONG):**
```python
schedule_data = {
    'scrape_interval_hours': 24  # ❌ Wrong column name
}
```

**After (CORRECT):**
```python
schedule_data = {
    'scraping_interval_hours': 24  # ✅ Correct column name
}
```

---

## 🔍 Root Cause Analysis

### Why Did This Happen?

1. **Inconsistent Naming Convention**
   - Database uses GraphQL API field names: `stat_count_*`, `stat_score_*`
   - Code was using simplified names: `views`, `rating_value`, `view_count`
   - These never matched!

2. **JSON vs String Confusion**
   - Database columns are `JSON` type for arrays
   - Code was converting to comma-separated strings
   - SQLAlchemy rejected this

3. **Typo in Schedule Column**
   - Schema: `scraping_interval_hours` (with -ing)
   - Code: `scrape_interval_hours` (without -ing)

4. **No Validation**
   - Errors were logged but execution continued
   - User saw "success" message despite all failures
   - Silent failures = invisible bugs

---

## 🧪 Testing

### Before Fix
```bash
# Add Bato link via button
# Result: "✅ Initial Bato scraping completed: 59 chapters found"
# But database check shows:
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
details = repo.get_manga_details(155461)
print(details)  # None ❌
"
```

### After Fix
```bash
# Add Bato link via button
# Result: "✅ Initial Bato scraping completed: 59 chapters found"
# Database check should show:
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
details = repo.get_manga_details(155461)
print(details)  # <BatoMangaDetails object> ✅
print(f'Name: {details.name}')
print(f'Upload Status: {details.upload_status}')
"
```

### Verification Checklist

After clicking "Add Bato Link" button, verify:

1. **Manga Details Table:**
   ```sql
   SELECT COUNT(*) FROM bato_manga_details WHERE anilist_id = YOUR_ID;
   -- Should return: 1
   ```

2. **Chapters Table:**
   ```sql
   SELECT COUNT(*) FROM bato_chapters WHERE anilist_id = YOUR_ID;
   -- Should return: 59 (or however many chapters exist)
   ```

3. **Schedule Table:**
   ```sql
   SELECT * FROM bato_scraping_schedule WHERE anilist_id = YOUR_ID;
   -- Should return: 1 row with next_scrape_at set to ~24h from now
   ```

4. **Log Table:**
   ```sql
   SELECT * FROM bato_scraper_log WHERE anilist_id = YOUR_ID ORDER BY scraped_at DESC LIMIT 1;
   -- Should return: 1 row with status='success', chapters_found=59
   ```

---

## 📊 Database Schema Reference

### Correct Column Names

#### `bato_manga_details`
```python
# Basic info
name, alt_names (JSON), authors (JSON), artists (JSON), genres (JSON)

# Publication
orig_lang, original_status, original_pub_from, original_pub_till, read_direction

# Bato-specific
upload_status

# Rating (stat_score_*)
stat_score_val, stat_count_votes, stat_count_scores (JSON)

# Statistics (stat_count_*)
stat_count_follows, stat_count_reviews, stat_count_post_reply, stat_count_views_total

# Emotions
stat_count_emotions (JSON)

# Content
summary
```

#### `bato_chapters`
```python
# Identifiers
bato_chapter_id, canonical_chapter_id

# Chapter info
chapter_number, dname, title, url_path, full_url

# Dates
date_create, date_public

# Statistics (stat_count_*)
stat_count_views_guest, stat_count_views_login, stat_count_views_total, stat_count_post_reply

# User tracking
is_read
```

#### `bato_scraping_schedule`
```python
# Scheduling
scraping_interval_hours  # ⚠️ Note the -ing!
last_scraped_at, next_scrape_at

# Pattern analysis
average_release_interval_days, preferred_release_day, release_pattern_confidence

# Statistics
total_chapters_tracked, last_chapter_date, consecutive_no_update_count

# Status
is_active, priority
```

---

## 🚀 Next Steps

### 1. Test the Fix

Re-test the manga that failed ("Run, Meil"):
```bash
# Click "Add Bato Link" button again
# Enter: https://batotwo.com/title/137197-run-meil-official
# Check logs for no errors
# Verify all 4 tables have data
```

### 2. Clean Up Failed Attempt

The previous failed attempt left partial data:
```sql
-- Check if bato_link exists in manga_list but nothing in bato tables
SELECT m.id_anilist, m.title_english, m.bato_link
FROM manga_list m
LEFT JOIN bato_manga_details b ON m.id_anilist = b.anilist_id
WHERE m.bato_link LIKE '%batotwo.com%'
  AND b.id IS NULL;
```

If you find any, either:
- Re-add the link via button (will create all entries)
- Or manually clean up the bato_link if you don't want it

### 3. Monitor Future Additions

Check logs after adding new Bato links:
```bash
# Should see these SUCCESS messages:
✅ Saved Bato manga details for [MANGA_NAME]
✅ Saved XX Bato chapters for [MANGA_NAME]
✅ Created initial Bato schedule for [MANGA_NAME]

# Should NOT see these ERROR messages:
❌ Unconsumed column names
❌ invalid keyword argument
❌ foreign key constraint fails
```

---

## 📚 Related Files

- **Schema Definition:** `app/models/bato_models.py`
- **Button Handler:** `app/blueprints/manga.py` (line ~130-240)
- **GraphQL Scrapers:**
  - `app/scraper/bato_graphql_hidden_api/bato_chapters_list_graphql.py`
  - `app/scraper/bato_graphql_hidden_api/bato_manga_details_graphql.py`
- **Repository:** `app/database_module/bato_repository.py`

---

## 💡 Lessons Learned

1. **Always validate column names** against actual schema
2. **Check data types** - JSON vs String, Integer vs Float
3. **Watch for typos** in column names (scrape vs scraping)
4. **Don't trust success messages** - verify in database
5. **Foreign key constraints are your friend** - they catch orphaned data
6. **Silent failures are dangerous** - should have raised exceptions instead of logging warnings

---

## ✅ Status

**Fixed:** October 24, 2025  
**Tested:** Pending user verification  
**Impact:** HIGH - All new manga additions via button were failing  
**Severity:** CRITICAL - Core feature completely broken

