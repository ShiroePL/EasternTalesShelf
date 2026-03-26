# Bato System - Complete Workflow Chain

## 🔗 The Complete Chain: From "Add Bato Link" Button to Ongoing Scraping

This document explains the **complete workflow** of how manga enters the Bato notification system and gets continuously scraped.

---

## 📋 Overview

The Bato system has **TWO entry points**:

1. **Initial Population** - For existing titles that already have `bato_link` (using `populate_bato_system_fresh.py`)
2. **New Titles** - When user adds a Bato link via the "Add Bato Link" button ⭐ **NEW FIX**

---

## 🆕 New Title Workflow (Add Bato Link Button)

### Before Fix ❌

```
User adds new title to manga_list
    ↓
User clicks "Add Bato Link" button
    ↓
User enters Bato.to URL
    ↓
/add_bato endpoint:
  - Updates manga_list.bato_link ✅
  - Extracts MangaUpdates link ✅
  - Fetches MangaUpdates data ✅
  - Emits WebSocket update ✅
    ↓
❌ NOTHING ELSE HAPPENS - Bato data NOT created!
    ↓
Bato container ignores this manga (no schedule entry)
    ↓
⚠️ User never gets chapter notifications!
```

### After Fix ✅

```
User adds new title to manga_list
    ↓
User clicks "Add Bato Link" button
    ↓
User enters Bato.to URL (e.g., https://bato.to/title/110100-my-manga)
    ↓
/add_bato endpoint:
  1. Updates manga_list.bato_link ✅
  2. Extracts MangaUpdates link from Bato page ✅
  3. Fetches MangaUpdates data via API ✅
  4. Emits WebSocket update for MangaUpdates ✅
  
  🆕 5. TRIGGERS INITIAL BATO SCRAPING:
     a. Extracts bato_id from URL (e.g., "110100")
     b. Scrapes manga details via GraphQL
     c. Scrapes all chapters via GraphQL
     d. Saves to bato_manga_details table
     e. Saves chapters to bato_chapters table
     f. Creates schedule in bato_scraping_schedule (24h interval)
     g. Logs initial scrape in bato_scraper_log
    ↓
Bato container picks up manga on next cycle (every 5 min)
    ↓
🎉 Ongoing scraping and notifications work automatically!
```

---

## 🔄 Ongoing Scraping Workflow (Bato Container)

Once a manga is in the system (via button or populate script), the container handles it:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bato Service Container                        │
│                 (runs every 5 minutes)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
    1. Query bato_scraping_schedule for manga where:
       next_scrape_at <= NOW
                              │
                              ↓
    2. For each manga due for scraping:
       ┌──────────────────────────────────────────────┐
       │ Sequential Processing (one at a time)       │
       ├──────────────────────────────────────────────┤
       │ a. Fetch chapters via GraphQL API           │
       │ b. Fetch manga details via GraphQL API      │
       │ c. Compare with existing chapters in DB     │
       │ d. If new chapters found:                   │
       │    - Insert into bato_chapters              │
       │    - Create notification in                 │
       │      bato_notifications table               │
       │      (is_emitted = FALSE)                   │
       │ e. Analyze release pattern                  │
       │ f. Calculate next_scrape_at                 │
       │ g. Update bato_scraping_schedule            │
       │ h. Log to bato_scraper_log                  │
       │                                              │
       │ WAIT 4-7 seconds (randomized)               │
       │ ↓                                            │
       │ Next manga...                                │
       └──────────────────────────────────────────────┘
                              │
                              ↓
    3. Sleep for 5 minutes
                              │
                              ↓
    4. Repeat
```

---

## 🔔 Notification Delivery

```
┌─────────────────────────────────────────────────────────────────┐
│                    Main Web Container                            │
│         (BatoNotificationPoller - runs every 60s)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
    1. Query bato_notifications WHERE is_emitted = FALSE
                              │
                              ↓
    2. For each notification:
       - Emit via SocketIO to connected users
       - Mark is_emitted = TRUE
                              │
                              ↓
    3. Users see real-time notification in drawer
                              │
                              ↓
    4. Sleep for 60 seconds, repeat
```

---

## 📊 Database Tables Involved

### Initial Setup (Button Click)

| Table | What Gets Created |
|-------|------------------|
| `manga_list` | `bato_link` field updated |
| `bato_manga_details` | ✨ **NEW**: Full manga metadata |
| `bato_chapters` | ✨ **NEW**: All current chapters |
| `bato_scraping_schedule` | ✨ **NEW**: Schedule entry (24h interval) |
| `bato_scraper_log` | ✨ **NEW**: Initial scrape log entry |

### Ongoing Operations (Container)

| Table | When Updated |
|-------|--------------|
| `bato_manga_details` | Every scrape (status, views, rating updated) |
| `bato_chapters` | When new chapters found |
| `bato_notifications` | When new chapters found or status changes |
| `bato_scraping_schedule` | After every scrape (next_scrape_at calculated) |
| `bato_scraper_log` | After every scrape (success/failure logged) |

---

## 🎯 Key Points

### ✅ What Works Now

1. **User adds Bato link** → Immediate initial scraping happens
2. **Initial data is created** → Manga visible to container
3. **Container picks it up** → Ongoing scraping starts automatically
4. **Pattern learning** → Scraping interval optimizes over time
5. **Notifications** → Real-time alerts when new chapters appear

### 🔧 Technical Details

**Rate Limiting (Respects Bato.to API):**
- Sequential scraping (one manga at a time)
- 4-7 second randomized delays between manga
- For 300 manga: ~25-35 minutes total per cycle
- Container runs every 5 minutes, but only scrapes manga that are DUE

**Initial Scraping (Button Click):**
- Happens synchronously in the request
- User sees immediate feedback
- Takes ~2-5 seconds per manga
- Creates complete initial dataset

**Ongoing Scraping (Container):**
- Runs in background, separate from web app
- No user interaction needed
- Handles errors gracefully with retries
- Logs everything for monitoring

---

## 🐛 Troubleshooting

### "I added a Bato link but no notifications appear"

**Check these:**

1. **Did initial scraping succeed?**
   ```bash
   doppler run -- python -c "
   from app.database_module.bato_repository import BatoRepository
   repo = BatoRepository()
   details = repo.get_manga_details(YOUR_ANILIST_ID)
   print('Bato details exist:', details is not None)
   "
   ```

2. **Is there a schedule entry?**
   ```bash
   doppler run -- python -c "
   from app.database_module.bato_repository import BatoRepository
   repo = BatoRepository()
   schedule = repo.get_schedule(YOUR_ANILIST_ID)
   print('Schedule:', schedule.next_scrape_at if schedule else 'NOT FOUND')
   "
   ```

3. **Check scraping logs:**
   ```bash
   doppler run -- python check_bato_logs.py
   ```

4. **Check container is running:**
   ```bash
   docker-compose ps bato-scraping-service
   docker-compose logs --tail=50 bato-scraping-service
   ```

### "Bato container not picking up new manga"

**Possible causes:**
- Container not running: `docker-compose up -d bato-scraping-service`
- Schedule not created: Check step 1 above
- next_scrape_at in the future: Wait for scheduled time
- Database connection issues: Check logs

---

## 📝 Example: Adding a New Manga

### Step-by-Step

1. **User adds manga to collection via AniList sync**
   - Manga appears in grid
   - No Bato link yet

2. **User clicks manga, then "Add Bato Link" button**
   - Prompt appears

3. **User enters Bato URL:**
   ```
   https://bato.to/title/110100-my-amazing-manga
   ```

4. **Backend processes request:**
   ```
   [INFO] Processing link for My Amazing Manga (AniList ID: 123456)
   [INFO] 🔄 Triggering initial Bato scraping for bato_id: 110100
   [INFO] 📚 Fetching Bato manga details for My Amazing Manga...
   [INFO] 📖 Fetching Bato chapters for My Amazing Manga...
   [INFO] ✅ Saved Bato manga details for My Amazing Manga
   [INFO] ✅ Saved 45 Bato chapters for My Amazing Manga
   [INFO] ✅ Created initial Bato schedule for My Amazing Manga (next scrape: 2025-10-25 12:00:00)
   [INFO] 🎉 Initial Bato scraping completed: 45 chapters found
   ```

5. **User sees success message:**
   ```
   "Bato link added successfully. Initial Bato scraping completed: 45 chapters found"
   ```

6. **Manga now in system:**
   - Bato icon appears in grid
   - Chapter list available
   - Container will scrape in 24 hours
   - When new chapter appears → Notification!

---

## 🚀 Production Deployment

### First Time Setup

1. **Run migrations:**
   ```bash
   doppler run -- python app/migrations/create_bato_tables_mariadb.py
   doppler run -- python app/migrations/add_is_emitted_to_bato_notifications.py
   ```

2. **Populate existing manga:**
   ```bash
   doppler run -- python populate_bato_system_fresh.py --limit 10  # Test first
   doppler run -- python populate_bato_system_fresh.py  # Full population
   ```

3. **Start containers:**
   ```bash
   docker-compose up -d
   ```

4. **Verify both services running:**
   ```bash
   docker-compose ps
   ```

### Adding New Manga (Ongoing)

Just click "Add Bato Link" button - everything else is automatic!

---

## 📈 Monitoring

### Admin Dashboard

Visit `/admin/bato` to see:
- Success/failure rates
- Average scraping duration
- Recent scraping logs
- System status

### Log Files

```
logs/bato/bato.log              - General operations
logs/bato/bato_errors.log       - Errors only
logs/bato/bato_performance.log  - Performance metrics
```

### Quick Status Check

```bash
# Check recent scraping activity
doppler run -- python check_bato_logs.py

# Check notification count
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
count = repo.get_notification_count(user_id=1)
print(f'Unread notifications: {count}')
"
```

---

## 🎉 Summary

The **complete chain** now works seamlessly:

```
Add Bato Link Button
  → Initial scraping (immediate)
    → Database entries created
      → Container sees manga
        → Ongoing scraping (automatic)
          → Notifications (real-time)
            → Happy users! 🎊
```

**No manual intervention needed after clicking the button!** 🚀
