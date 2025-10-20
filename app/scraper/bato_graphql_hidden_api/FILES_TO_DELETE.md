# Files to Delete - Cleanup List

**Date**: 2025-10-20  
**Reason**: Cleanup after migration from Playwright scraping to GraphQL API

---

## ✅ SAFE TO DELETE - Old Playwright Scrapers (Replaced by GraphQL)

These are the old scrapers that have been replaced by the new GraphQL versions:

```
bato_manga_details_scraper.py  → Replaced by: bato_manga_details_graphql.py
bato_chapters_list.py          → Replaced by: bato_chapters_list_graphql.py
```

---

## ✅ SAFE TO DELETE - Discovery/Investigation Files

These were used to discover and test the GraphQL API:

```
discover_full_api.py
discover_queries.py
discover_subscriptions.py
discover_mangaupdates.py
final_test.py
pattern_test.py
refine_test.py
test_graphql.py
try_grapg.py
scraping_html_something.py
mangaupdates_deep_dive.py
mangaupdates_slug_converter.py
```

---

## ✅ SAFE TO DELETE - Test Output/Result JSON Files

These are output files from testing and investigation:

```
102497-please-don-t-come-to-the-villainess-stationery-store.json
API_COMIC_DETAILS_FULL.json
API_COMIC_WITH_EMOTIONS.json
API_COMIC_WITH_RATINGS.json
API_COMIC_WITH_VIEWS.json
chapters_list_output.json
manga_details_output.json
FINAL_CHAPTERS_COMPLETE.json
FINAL_COMIC_COMPLETE.json
SUCCESS_Chapter_List_(ID_type).json
SUCCESS_Comic_Details_(ID_type).json
mangaupdates_series_48465726286.json
```

---

## ✅ SAFE TO DELETE - Test Output Folder

```
102497-please-don-t-come-to-the-villainess-stationery-store/  (entire folder)
```

---

## ⚠️ REVIEW BEFORE DELETING - Investigation Documentation

These are documentation files from the investigation phase. You might want to keep them for reference:

```
BATOTWO_SUBSCRIPTIONS_ANALYSIS.md  (probably not needed - subscriptions aren't used)
MANGAUPDATES_API_ANALYSIS.md      (if you're not using MangaUpdates API, delete it)
```

---

## ✅ KEEP - Essential Files

**DO NOT DELETE** these files:

```
batotwo_client.py                   ✅ KEEP - Reusable GraphQL client with CLI
bato_manga_details_graphql.py       ✅ KEEP - NEW GraphQL manga details scraper
bato_chapters_list_graphql.py       ✅ KEEP - NEW GraphQL chapters list scraper
bato_models.py                      ✅ KEEP - Data models (if still used)
final_complete_queries.py           ✅ KEEP - Working query examples/reference
BATOTWO_GRAPHQL_API_DOCS.md        ✅ KEEP - Important API documentation
STEALTH_AND_RATE_LIMITING.md       ✅ KEEP - Important for production usage
message.txt                         ✅ KEEP - (check what this is first)
batotwo_data/                       ✅ KEEP - Output folder for API responses
```

---

## 📝 Quick Delete Commands (PowerShell)

### Delete old scrapers:
```powershell
Remove-Item "bato_manga_details_scraper.py", "bato_chapters_list.py"
```

### Delete discovery/test files:
```powershell
Remove-Item "discover_full_api.py", "discover_queries.py", "discover_subscriptions.py", "discover_mangaupdates.py", "final_test.py", "pattern_test.py", "refine_test.py", "test_graphql.py", "try_grapg.py", "scraping_html_something.py", "mangaupdates_deep_dive.py", "mangaupdates_slug_converter.py"
```

### Delete test output JSON files:
```powershell
Remove-Item "102497-please-don-t-come-to-the-villainess-stationery-store.json", "API_COMIC_DETAILS_FULL.json", "API_COMIC_WITH_EMOTIONS.json", "API_COMIC_WITH_RATINGS.json", "API_COMIC_WITH_VIEWS.json", "chapters_list_output.json", "manga_details_output.json", "FINAL_CHAPTERS_COMPLETE.json", "FINAL_COMIC_COMPLETE.json", "SUCCESS_Chapter_List_(ID_type).json", "SUCCESS_Comic_Details_(ID_type).json", "mangaupdates_series_48465726286.json"
```

### Delete test folder:
```powershell
Remove-Item -Recurse -Force "102497-please-don-t-come-to-the-villainess-stationery-store"
```

### Delete investigation docs (optional):
```powershell
Remove-Item "BATOTWO_SUBSCRIPTIONS_ANALYSIS.md", "MANGAUPDATES_API_ANALYSIS.md"
```

### ALL IN ONE (nuclear option - review first!):
```powershell
Remove-Item "bato_manga_details_scraper.py", "bato_chapters_list.py", "discover_full_api.py", "discover_queries.py", "discover_subscriptions.py", "discover_mangaupdates.py", "final_test.py", "pattern_test.py", "refine_test.py", "test_graphql.py", "try_grapg.py", "scraping_html_something.py", "mangaupdates_deep_dive.py", "mangaupdates_slug_converter.py", "102497-please-don-t-come-to-the-villainess-stationery-store.json", "API_COMIC_DETAILS_FULL.json", "API_COMIC_WITH_EMOTIONS.json", "API_COMIC_WITH_RATINGS.json", "API_COMIC_WITH_VIEWS.json", "chapters_list_output.json", "manga_details_output.json", "FINAL_CHAPTERS_COMPLETE.json", "FINAL_COMIC_COMPLETE.json", "SUCCESS_Chapter_List_(ID_type).json", "SUCCESS_Comic_Details_(ID_type).json", "mangaupdates_series_48465726286.json", "BATOTWO_SUBSCRIPTIONS_ANALYSIS.md", "MANGAUPDATES_API_ANALYSIS.md"
Remove-Item -Recurse -Force "102497-please-don-t-come-to-the-villainess-stationery-store"
```

---

## 📊 Summary

- **Old scrapers to delete**: 2 files
- **Discovery/test scripts to delete**: 12 files  
- **Test output JSON to delete**: 12 files
- **Test folders to delete**: 1 folder
- **Optional docs to delete**: 2 files

**Total to delete**: ~29 files/folders

**After cleanup, you'll have**:
- `batotwo_client.py` - GraphQL client with CLI
- `bato_manga_details_graphql.py` - NEW manga details scraper
- `bato_chapters_list_graphql.py` - NEW chapters list scraper  
- `bato_models.py` - Data models
- `final_complete_queries.py` - Query examples
- `BATOTWO_GRAPHQL_API_DOCS.md` - API documentation
- `STEALTH_AND_RATE_LIMITING.md` - Production notes
- `batotwo_data/` - Output folder
- `message.txt` - (check this first)

---

**✅ This cleanup is safe because**:
1. Old Playwright scrapers are completely replaced by GraphQL versions
2. All discovery/test files were one-time investigation scripts
3. Test output JSONs are not used by any code
4. Essential files (client, new scrapers, docs) are preserved
