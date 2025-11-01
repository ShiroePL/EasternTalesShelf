# Batch Bato Links Processing

## Overview

This script (`batch_process_bato_links.py`) processes existing Bato links from your manga database and populates the Bato notification system with manga details, chapters, and schedules.

**Purpose:** Many manga in your database already have Bato links but weren't scraped when the Bato notification system was added. This script fills in that missing data.

## Features

✅ **Automatic Discovery** - Fetches all manga with Bato links from `manga_list` table  
✅ **Smart Skipping** - Skips manga that already have Bato data (configurable)  
✅ **Rate Limiting** - Random delays between requests (default: 5-15 seconds)  
✅ **Test Mode** - Process only N titles for testing before full run  
✅ **Progress Tracking** - Real-time progress and statistics  
✅ **Error Handling** - Comprehensive error logging and recovery  
✅ **Database Logging** - All operations logged to `bato_scraper_log` table

## What It Does

For each manga with a Bato link, the script:

1. **Extracts Bato ID** from the link
2. **Scrapes manga details** using the GraphQL API
3. **Scrapes all chapters** for the manga
4. **Saves to database:**
   - `bato_manga_details` - Manga info, ratings, statistics
   - `bato_chapters` - All chapters with metadata
   - `bato_scraping_schedule` - Schedule for future updates
   - `bato_scraper_log` - Processing history
5. **Adds random delay** before next manga (avoids API abuse)

## Usage

### Test Mode (Recommended First!)

Process only 3 manga to verify everything works:

```bash
python batch_process_bato_links.py --test 3
```

### Process All Manga

Process all manga with Bato links (default: 5-15 second delays):

```bash
python batch_process_bato_links.py
```

### Custom Delay Range

Process with longer delays (10-20 seconds) to be extra safe:

```bash
python batch_process_bato_links.py --min-delay 10 --max-delay 20
```

### Process Specific Number

Process first 10 manga:

```bash
python batch_process_bato_links.py --limit 10
```

### Reprocess Everything

Process all manga, even those already in the database:

```bash
python batch_process_bato_links.py --no-skip-existing
```

### Verbose Mode

Enable detailed logging from the scrapers:

```bash
python batch_process_bato_links.py --test 3 --verbose
```

## Command-Line Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--test N` | int | Test mode: process only N manga |
| `--limit N` | int | Process only N manga (same as test) |
| `--min-delay` | float | Minimum delay in seconds (default: 5.0) |
| `--max-delay` | float | Maximum delay in seconds (default: 15.0) |
| `--no-skip-existing` | flag | Process even already-processed manga |
| `--verbose` / `-v` | flag | Enable verbose scraper logging |

## Output & Logging

### Console Output

Real-time progress with:
- Current manga being processed
- Scraping status (details, chapters)
- Success/failure messages
- Progress counter (e.g., "5/300")
- Random delay countdown

### Log Files

Detailed logs saved to: `logs/batch_bato_processing_YYYYMMDD_HHMMSS.log`

Contains:
- All console output
- Detailed error traces
- Database operations
- API responses (if verbose)

### Final Statistics

At the end of processing, you'll see:

```
📊 FINAL STATISTICS
================================================================================
Total manga found:         300
Already processed:         50
Successfully processed:    240
Failed:                    10
Skipped:                   0

❌ ERRORS:
  - Manga Title (ID: 12345)
    Error: Connection timeout
```

## Example Run

```bash
$ python batch_process_bato_links.py --test 3

================================================================================
🚀 Starting Bato Batch Processing
================================================================================
Configuration:
  - Min delay: 5.0s
  - Max delay: 15.0s
  - Skip existing: True
  - Limit: 3

Found 300 manga with Bato links

📊 Progress: 1/3
================================================================================
Processing: The Villainess Stationery Shop (AniList ID: 123456)
Bato Link: https://batotwo.com/title/110100-the-villainess...
Extracted Bato ID: 110100
📚 Fetching Bato manga details...
📖 Fetching Bato chapters...
Found 45 chapters
✅ Saved Bato manga details
✅ Saved 45 Bato chapters
✅ Created Bato schedule (next scrape: 2025-11-02 15:30:00)
🎉 Successfully processed The Villainess Stationery Shop
   - Details saved
   - 45 chapters saved
   - Schedule created

⏳ Waiting 8.42 seconds before next request...

[... continues for remaining manga ...]

📊 FINAL STATISTICS
================================================================================
Total manga found:         3
Already processed:         0
Successfully processed:    3
Failed:                    0
Skipped:                   0
================================================================================
✅ Batch processing complete!
================================================================================
```

## Safety Features

### Rate Limiting
- **Random delays** between requests (5-15 seconds by default)
- **Configurable** delays via command-line arguments
- Prevents API abuse and rate limiting

### Smart Skipping
- **Checks existing data** before processing
- Skips manga that already have Bato details
- Option to reprocess if needed

### Error Recovery
- **Continues on errors** - one failed manga doesn't stop the whole batch
- **Logs all errors** with full stack traces
- **Tracks statistics** for failed items

### Database Safety
- **Uses existing repository** - same code as production Bato system
- **Upsert operations** - won't duplicate data
- **Transaction handling** - proper rollback on errors

## Troubleshooting

### "No manga with Bato links found"
**Cause:** Your database doesn't have manga with `bato_link` populated  
**Solution:** Add Bato links manually using the web interface first

### "Failed to fetch manga details"
**Cause:** Invalid Bato ID or API connection issue  
**Solution:** Check the log file for details, verify Bato link format

### "Connection timeout" errors
**Cause:** Network issues or Bato API rate limiting  
**Solution:** Increase delays with `--min-delay 15 --max-delay 30`

### Database connection errors
**Cause:** Database server not running or connection issues  
**Solution:** Check database configuration in `app/config.py`

### Import errors
**Cause:** Script not finding app modules  
**Solution:** Run from project root directory: `python batch_process_bato_links.py`

## Best Practices

### 1. Test First
Always run with `--test 3` first to verify everything works:
```bash
python batch_process_bato_links.py --test 3
```

### 2. Use Appropriate Delays
For large batches (100+ manga), use longer delays:
```bash
python batch_process_bato_links.py --min-delay 10 --max-delay 20
```

### 3. Process in Batches
For 300+ manga, process in chunks:
```bash
python batch_process_bato_links.py --limit 50
# Wait a few hours
python batch_process_bato_links.py --limit 50
# Etc.
```

### 4. Monitor Logs
Keep an eye on the log file for errors:
```bash
tail -f logs/batch_bato_processing_*.log
```

### 5. Run During Off-Peak Hours
Process large batches during low-traffic periods to avoid API issues

## Database Tables Affected

| Table | Purpose | What Gets Saved |
|-------|---------|-----------------|
| `bato_manga_details` | Manga information | Name, authors, genres, ratings, stats |
| `bato_chapters` | Chapter list | All chapters with numbers, titles, dates |
| `bato_scraping_schedule` | Update schedule | When to check for new chapters |
| `bato_scraper_log` | Processing history | Success/failure logs for each run |

## Integration with Existing System

This script uses the **exact same code** as the "Add Bato Link" button:
- ✅ Same scrapers (`BatoChaptersListGraphQL`, `BatoMangaDetailsGraphQL`)
- ✅ Same repository (`BatoRepository`)
- ✅ Same database models (`bato_models.py`)
- ✅ Same data format

**Result:** Data is 100% compatible with your existing Bato notification system!

## After Running

Once processed, manga will:
- ✅ Appear in Bato admin dashboard
- ✅ Be checked for new chapters automatically
- ✅ Generate notifications when new chapters appear
- ✅ Show chapter counts and details in UI

## Estimated Time

Processing time depends on:
- Number of manga to process
- Delay settings
- Number of chapters per manga

**Example calculation:**
- 300 manga × 10 seconds average delay = **~50 minutes**
- Plus scraping time (~2-5 seconds per manga) = **~60-75 minutes total**

## Support

If you encounter issues:
1. Check the log file in `logs/`
2. Verify database connection
3. Test with `--test 1` first
4. Ensure Bato links are valid
5. Check network connectivity

## Author

Created by Shiro for the EasternTalesShelf project  
Date: 2025-11-01
