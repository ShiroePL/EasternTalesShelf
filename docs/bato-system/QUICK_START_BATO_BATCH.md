# Quick Start Guide - Batch Bato Processing

## 🚀 Getting Started in 3 Steps

### Step 1: Test with 1 Manga
```bash
python batch_process_bato_links.py --test 1
```

This will:
- Process just 1 manga to verify everything works
- Show you exactly what the script does
- Take less than 30 seconds

### Step 2: Test with 3 Manga
```bash
python batch_process_bato_links.py --test 3
```

This will:
- Process 3 manga to ensure stability
- Give you confidence before full run
- Take about 1-2 minutes

### Step 3: Run Full Batch (Safe Mode)
```bash
python batch_process_bato_links.py --min-delay 10 --max-delay 20
```

This will:
- Process all manga with Bato links
- Use safe delays (10-20 seconds) to avoid API issues
- Take ~50-75 minutes for 300 manga
- Skip manga that already have Bato data

## 📊 What to Expect

### Console Output
```
================================================================================
🚀 Starting Bato Batch Processing
================================================================================
Configuration:
  - Min delay: 10.0s
  - Max delay: 20.0s
  - Skip existing: True
  - Limit: None (process all)

Found 300 manga with Bato links

📊 Progress: 1/300
================================================================================
Processing: The Villainess Stationery Shop (AniList ID: 123456)
Bato Link: https://batotwo.com/title/110100-...
Extracted Bato ID: 110100
📚 Fetching Bato manga details...
📖 Fetching Bato chapters...
Found 45 chapters
✅ Saved Bato manga details
✅ Saved 45 Bato chapters
✅ Created Bato schedule
🎉 Successfully processed The Villainess Stationery Shop

⏳ Waiting 12.34 seconds before next request...
```

### Final Statistics
```
📊 FINAL STATISTICS
================================================================================
Total manga found:         300
Already processed:         50
Successfully processed:    240
Failed:                    10
================================================================================
✅ Batch processing complete!
```

## 🔍 Checking Results

After running, check your database:

1. **Bato Admin Dashboard** - Should show all processed manga
2. **Database Tables:**
   - `bato_manga_details` - Should have new entries
   - `bato_chapters` - Should have all chapters
   - `bato_scraping_schedule` - Should have schedules
   - `bato_scraper_log` - Should have processing logs

## ⚠️ Common Issues

### Issue: "No manga with Bato links found"
**Solution:** Your database needs manga with `bato_link` populated first

### Issue: Script fails immediately
**Solution:** Make sure you're in the project root directory:
```bash
cd "d:\111111.PROGRAMOWANIE\AI W PYTHONIE\EasternTalesShelf"
python batch_process_bato_links.py --test 1
```

### Issue: Import errors
**Solution:** Activate your virtual environment:
```bash
.\.venv\Scripts\Activate.ps1
python batch_process_bato_links.py --test 1
```

### Issue: Too many errors during processing
**Solution:** Increase delays to avoid rate limiting:
```bash
python batch_process_bato_links.py --min-delay 15 --max-delay 30
```

## 💡 Pro Tips

### Tip 1: Process in Smaller Batches
For 300+ manga, process in chunks:
```bash
# First batch (50 manga)
python batch_process_bato_links.py --limit 50

# Wait 1-2 hours, then next batch
python batch_process_bato_links.py --limit 50

# Continue until done
```

### Tip 2: Run Overnight
For large batches, run overnight:
```bash
python batch_process_bato_links.py --min-delay 15 --max-delay 25 > batch_output.txt 2>&1
```

### Tip 3: Monitor Progress
In another terminal, watch the log:
```bash
Get-Content -Path "logs\batch_bato_processing_*.log" -Wait -Tail 20
```

### Tip 4: Resume After Interruption
The script automatically skips already-processed manga, so you can safely interrupt and restart:
```bash
# Press Ctrl+C to stop
# Later, just run again - it will skip completed manga
python batch_process_bato_links.py
```

## 📝 All Available Commands

```bash
# Basic test
python batch_process_bato_links.py --test 3

# Process all with default delays (5-15 seconds)
python batch_process_bato_links.py

# Safe mode with longer delays
python batch_process_bato_links.py --min-delay 10 --max-delay 20

# Process specific amount
python batch_process_bato_links.py --limit 50

# Verbose mode (detailed logs)
python batch_process_bato_links.py --test 3 --verbose

# Reprocess everything (including already-processed)
python batch_process_bato_links.py --no-skip-existing

# Help and all options
python batch_process_bato_links.py --help
```

## ⏱️ Time Estimates

| Manga Count | Delay Range | Estimated Time |
|-------------|-------------|----------------|
| 1 (test) | 5-15s | ~10 seconds |
| 3 (test) | 5-15s | ~30 seconds |
| 10 | 5-15s | ~2 minutes |
| 50 | 10-20s | ~15 minutes |
| 100 | 10-20s | ~30 minutes |
| 300 | 10-20s | ~75 minutes |

## ✅ Verification Checklist

After running the script:

- [ ] Check console output for final statistics
- [ ] Verify log file has no major errors
- [ ] Check Bato admin dashboard shows new manga
- [ ] Verify `bato_manga_details` table has new entries
- [ ] Confirm `bato_chapters` table has chapters
- [ ] Check `bato_scraping_schedule` has schedules
- [ ] Look at `bato_scraper_log` for processing history

## 🆘 Need Help?

1. Check the full documentation: `BATCH_BATO_PROCESSING_README.md`
2. Review log files in `logs/` directory
3. Run with `--verbose` flag for detailed output
4. Test with just 1 manga first to isolate issues

## 🎯 Recommended First Run

```bash
# Activate environment
.\.venv\Scripts\Activate.ps1

# Navigate to project root
cd "d:\111111.PROGRAMOWANIE\AI W PYTHONIE\EasternTalesShelf"

# Test with 1 manga first
python batch_process_bato_links.py --test 1

# If successful, test with 3
python batch_process_bato_links.py --test 3

# If all good, run full batch with safe delays
python batch_process_bato_links.py --min-delay 10 --max-delay 20
```

Good luck! 🚀
