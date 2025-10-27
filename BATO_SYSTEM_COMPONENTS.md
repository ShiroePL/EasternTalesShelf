# Bato Notification System - Complete Component Map

This document lists all files created/modified for the batotwo.com notification system, organized by layer.

---

## 📊 Database Layer

### `app/models/bato_models.py` ✨ NEW
**Purpose:** SQLAlchemy database models for all Bato tables

**Models:**
- `BatoMangaDetails` - Stores manga metadata from Bato.to (name, authors, genres, stats, etc.)
- `BatoChapters` - Individual chapter records with URLs and view counts
- `BatoNotifications` - User notifications for new chapters and status changes
- `BatoScraperLog` - Logs all scraping jobs for monitoring
- `BatoScrapingSchedule` - Intelligent scheduling with pattern analysis

**Key Function:**
- `init_bato_db(engine)` - Initializes all Bato tables

---

### `app/database_module/bato_repository.py` ✨ NEW
**Purpose:** Data access layer - all database operations for Bato tables

**Methods:**
- **Manga Details:** `get_manga_details()`, `upsert_manga_details()`
- **Chapters:** `get_chapters()`, `bulk_insert_chapters()`, `get_existing_chapter_ids()`, `get_chapter_dates()`
- **Notifications:** `create_notification()`, `get_unread_notifications()`, `mark_notification_read()`, `get_notification_count()`
- **Scheduling:** `get_schedule()`, `upsert_schedule()`, `get_manga_due_for_scraping()`, `update_schedule_after_scrape()`
- **Logging:** `log_scraping_job()`, `get_scraping_stats()`, `get_recent_logs()`

**Features:**
- Thread-safe using scoped_session
- Handles SQLite and MariaDB differences
- Comprehensive error handling (duplicates, deadlocks, foreign keys)

---

## 🕷️ Scraper Layer

### `app/scraper/bato_graphql_hidden_api/bato_chapters_list_graphql.py` ✨ NEW
**Purpose:** GraphQL scraper for fetching chapter lists from Bato.to

**Class:** `BatoChaptersListGraphQL`

**Key Method:**
- `scrape_chapters(manga_id, get_manga_title=True)` - Returns dict with chapters array and manga title

**Features:**
- Uses hidden GraphQL API endpoint
- Transforms API data to match database schema
- Handles pagination (up to 1000 chapters)
- Verbose logging option

---

### `app/scraper/bato_graphql_hidden_api/bato_manga_details_graphql.py` ✨ NEW
**Purpose:** GraphQL scraper for fetching manga metadata from Bato.to

**Class:** `BatoMangaDetailsGraphQL`

**Key Method:**
- `scrape_manga_details(manga_id)` - Returns dict with all manga metadata

**Features:**
- Fetches comprehensive manga info (authors, genres, stats, summary)
- Transforms nested GraphQL response to flat structure
- Handles missing/null fields gracefully




---

## 🧠 Business Logic Layer

### `app/services/bato/bato_scraping_service.py` ✨ NEW (🔧 MODIFIED for containerization)
**Purpose:** Background service that orchestrates all scraping operations

**Class:** `BatoScrapingService`

**Key Methods:**
- `start()` - Starts background thread
- `stop()` - Gracefully stops service
- `run_loop()` - Main loop (runs every 5 minutes)
- `execute_scraping_job(manga_data)` - Scrapes one manga
- `process_scraping_results()` - Updates database and creates notifications

**Features:**
- **Sequential scraping with rate limiting** - Processes manga one at a time
- **Human-like delays** - Randomized 4-7 second delays between each manga scrape
- **Respects Bato.to API** - Mimics human browsing behavior to avoid detection
- Retry logic with exponential backoff
- Rate limiting detection (429 responses)
- Comprehensive error handling and logging
- **Standalone mode:** Can run without Flask app context or SocketIO
- **Notification polling:** Writes notifications to database for web app to poll

**Rate Limiting Strategy:**
- Scrapes manga sequentially (one at a time, not concurrent)
- Waits 4-7 seconds (randomized) between each manga
- Both chapter list and manga details are fetched together (as they load on same page)
- For 300 manga: ~25-35 minutes total scraping time per cycle
- Service runs every 5 minutes, but only scrapes manga that are due based on their schedule

---

### `app/services/bato/chapter_comparator.py` ✨ NEW
**Purpose:** Detects new chapters by comparing scraped vs database data

**Class:** `ChapterComparator`

**Key Methods:**
- `find_new_chapters(anilist_id, scraped_chapters)` - Returns list of new chapters
- `should_create_batch_notification(new_chapters)` - True if 3+ chapters

**Logic:**
- Compares `bato_chapter_id` to detect new chapters
- Efficient set-based comparison

---

### `app/services/bato/pattern_analyzer.py` ✨ NEW
**Purpose:** Analyzes release patterns to optimize scraping schedules

**Class:** `PatternAnalyzer`

**Key Methods:**
- `calculate_average_interval(chapter_dates)` - Returns average days between releases
- `detect_weekly_pattern(chapter_dates)` - Finds preferred release day (0=Monday, 6=Sunday)
- `calculate_confidence_score(chapter_dates, preferred_day)` - Pattern confidence 0.0-1.0
- `predict_next_release_date(chapter_dates)` - Predicts next chapter date

**Features:**
- Requires minimum 3 chapters for interval analysis
- Requires minimum 5 chapters for weekly pattern detection
- 60% threshold for pattern confidence

---

### `app/services/bato/scheduling_engine.py` ✨ NEW
**Purpose:** Calculates optimal scraping schedules based on patterns

**Class:** `SchedulingEngine`

**Key Methods:**
- `calculate_next_scrape_time(anilist_id, manga_data)` - Returns next scrape datetime
- `update_schedule_after_scrape(anilist_id, new_chapters_found)` - Adjusts schedule
- `adjust_for_no_updates(schedule)` - Increases interval if no new chapters

**Rules:**
- Default: 24 hours for new manga
- Pattern-based: 80% of average interval
- Minimum: 6 hours
- Maximum: 14 days
- Completed/Dropped: 30 days

---

### `app/services/bato/notification_manager.py` ✨ NEW
**Purpose:** Creates and manages notifications for manga updates

**Class:** `NotificationManager`

**Key Methods:**
- `create_new_chapter_notification(chapter_data)` - Single chapter (importance=1)
- `create_batch_notification(manga_data, chapters)` - Multiple chapters (importance=2)
- `create_status_change_notification(manga_data, old_status, new_status)` - Status change (importance=3)
- `emit_websocket_notification(notification_data)` - Sends real-time notification via SocketIO

**Features:**
- Importance levels for sorting
- WebSocket integration for real-time updates
- Comprehensive notification data structure

---

### `app/services/bato/error_handler.py` ✨ NEW
**Purpose:** Centralized error handling with retry logic

**Features:**
- `@with_retry` decorator for automatic retries
- Rate limiting detection and management
- Network error handling
- Database error handling (deadlocks, duplicates)

---

### `app/services/bato/error_monitor.py` ✨ NEW
**Purpose:** Monitors error rates and system health

**Functions:**
- `record_error(error_type, message, manga_id)` - Logs errors
- `record_performance(operation, duration, manga_id)` - Tracks performance
- `get_monitor()` - Returns ErrorMonitor singleton

**Features:**
- Tracks error rates over time
- Alerts when error rate exceeds 10% over 24 hours
- Performance monitoring

---

### `app/services/bato/logging_config.py` ✨ NEW
**Purpose:** Logging configuration for Bato system

**Functions:**
- `init_logging(log_level, log_to_file)` - Initializes logging
- `get_bato_logger(name)` - Returns configured logger

**Log Files:**
- `logs/bato/bato.log` - General operations
- `logs/bato/bato_errors.log` - Errors only
- `logs/bato/bato_performance.log` - Performance metrics

---

### `app/services/bato/database_connection_handler.py` ✨ NEW
**Purpose:** Robust database connection management for standalone Bato service

**Class:** `DatabaseConnectionHandler`

**Key Methods:**
- `initialize()` - Initializes database engine with connection pooling
- `verify_connection()` - Verifies connectivity with retry logic
- `get_session()` - Context manager for database sessions
- `execute_with_retry(operation)` - Executes operations with retry logic
- `dispose()` - Cleans up connections gracefully
- `get_pool_status()` - Returns connection pool statistics

**Features:**
- Connection pooling (size=10, max_overflow=5, recycle=3600s)
- Pre-ping to test connections before use
- Automatic reconnection on connection loss
- "MySQL server has gone away" error handling
- Exponential backoff retry logic (max 5 attempts)
- Thread-safe session management with scoped_session
- Connection pool monitoring and statistics

**Configuration:**
- `POOL_SIZE = 10` - Number of connections to maintain
- `MAX_OVERFLOW = 5` - Additional connections when pool is full
- `POOL_RECYCLE = 3600` - Recycle connections after 1 hour
- `POOL_PRE_PING = True` - Test connections before using
- `MAX_RETRIES = 5` - Maximum retry attempts
- `INITIAL_RETRY_DELAY = 1` - Initial delay in seconds
- `MAX_RETRY_DELAY = 30` - Maximum delay in seconds

**Global Functions:**
- `get_db_handler()` - Get or create global handler instance
- `initialize_db_handler()` - Initialize global handler
- `dispose_db_handler()` - Dispose global handler

---

### `app/services/bato_notification_polling.py` ✨ NEW
**Purpose:** Polls database for new Bato notifications and emits via SocketIO

**Class:** `BatoNotificationPoller`

**Key Methods:**
- `start()` - Starts polling service in background thread
- `stop()` - Stops polling service gracefully
- `_poll_loop()` - Main polling loop (runs every 60 seconds)
- `_check_and_emit_notifications()` - Fetches and emits notifications
- `_format_notification(notif)` - Formats notification for SocketIO

**Features:**
- Runs as daemon thread in main web application
- Polls `bato_notifications` table every 60 seconds (configurable)
- Fetches notifications where `is_emitted = FALSE`
- Emits via SocketIO with event name `bato_notification`
- Marks notifications as emitted to prevent duplicates
- Broadcasts to all connected clients
- Comprehensive error handling and logging

**Configuration:**
- `poll_interval` - Seconds between polls (default: 60)
- Recommended: 60 seconds for good balance between real-time and database load

**Global Functions:**
- `init_bato_notification_poller(socketio, poll_interval)` - Initialize and start poller
- `get_poller_instance()` - Get global poller instance
- `stop_bato_notification_poller()` - Stop poller

**Integration:**
- Called in `app/app.py` after SocketIO initialization
- Bridges standalone Bato service container with web app
- Enables real-time notifications without direct container communication

---

## 🌐 API/Blueprint Layer

### `app/blueprints/bato_notifications.py` ✨ NEW
**Purpose:** REST API endpoints for notifications and chapters

**Routes:**
- `GET /api/bato/notifications` - Get unread notifications
- `POST /api/bato/notifications/<id>/read` - Mark notification as read
- `GET /api/bato/notifications/count` - Get unread count
- `GET /api/bato/chapters/<anilist_id>` - Get chapter list
- `GET /api/bato/schedule/<anilist_id>` - Get scraping schedule
- `POST /api/bato/scrape/<anilist_id>` - Manually trigger scrape

**Features:**
- Login required for all endpoints
- JSON responses
- Error handling

---

### `app/blueprints/bato_admin.py` ✨ NEW
**Purpose:** Admin dashboard for monitoring scraping system

**Routes:**
- `GET /admin/bato` - Admin dashboard page
- `GET /api/bato/admin/stats` - Scraping statistics
- `GET /api/bato/admin/system-status` - System status
- `GET /api/bato/admin/logs` - Recent scraping logs

**Features:**
- Admin access required
- Real-time statistics
- Activity charts
- Error monitoring

---

## 🎨 Frontend Layer

### `app/templates/pages/bato_admin.html` ✨ NEW
**Purpose:** Admin dashboard UI

**Features:**
- Statistics cards (success rate, error rate, average duration)
- Activity chart (Chart.js)
- Recent logs table
- System status banner
- Dark theme styling

---

### `app/templates/sections/_manga_grid.html` 🔧 MODIFIED
**Purpose:** Manga grid display

**Changes:**
- Added Bato notification indicators
- Updated grid item structure

---

### `app/templates/components/_notifications_app.html` 🔧 MODIFIED
**Purpose:** Notification drawer component

**Changes:**
- Added Bato notification types
- Updated notification rendering

---

### `app/templates/base.html` 🔧 MODIFIED
**Purpose:** Base template

**Changes:**
- Added Bato notification drawer
- Included notification scripts

---

### `app/static/js/notification-drawer.js` ✨ NEW
**Purpose:** Notification drawer functionality

**Features:**
- Fetches and displays Bato notifications
- Real-time updates via WebSocket
- Mark as read functionality
- Notification count badge

---



### `app/static/css/components/notifications.css` 🔧 MODIFIED
**Purpose:** Notification styling

**Changes:**
- Added Bato notification styles
- Importance level colors

---


## 🐳 Containerization

### `app/services/bato/bato_service_runner.py` ✨ NEW
**Purpose:** Standalone entry point for Bato service container

**Class:** `BatoServiceRunner`

**Key Methods:**
- `setup_logging()` - Configures logging for standalone mode
- `setup_signal_handlers()` - Handles SIGTERM/SIGINT for graceful shutdown
- `verify_database_connection()` - Tests DB connectivity before starting
- `run()` - Main loop with retry logic and error handling
- `shutdown()` - Graceful shutdown with 30-second timeout for active jobs

**Command-Line Arguments:**
- `--test` - Run in test mode with detailed logging
- `--limit N` - Process only N manga (for testing)
- `--once` - Run single scraping cycle then exit

**Features:**
- Runs BatoScrapingService in standalone mode (no Flask app context)
- Exponential backoff retry logic (max 5 attempts)
- Heartbeat logging every 5 minutes
- Handles "MySQL server has gone away" errors
- Thread-safe shutdown coordination

**Usage:**
```bash
# Normal operation
python -m app.services.bato.bato_service_runner

# Test mode with limit
python -m app.services.bato.bato_service_runner --test --limit 5

# Single run
python -m app.services.bato.bato_service_runner --once
```

---

### `docker-compose.yml` 🔧 MODIFIED
**Purpose:** Docker Compose orchestration

**New Service Added:**
```yaml
bato-scraping-service:
  image: easterntalesshelf:local
  restart: always
  container_name: EasternTalesShelf-bato-scraper-notifications
  environment:
    - FLASK_ENV=production
    - DOPPLER_TOKEN=${DOPPLER_TOKEN_EASTERN_SHELF}
  command: >
    doppler run -- python -m app.services.bato.bato_service_runner
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  networks:
    - external-containers
    - phpmyadmin_gpt_db
  volumes:
    - .:/app
    - logs_volume:/app/logs
```

**Features:**
- Separate container for Bato scraping service
- Shares same Docker image as main web container
- Automatic restart on failure
- Shared database access via Docker networks
- Shared log volume for centralized logging
- Doppler integration for secrets management

---

## 🔧 Application Integration

### `app/app.py` 🔧 MODIFIED
**Purpose:** Main Flask application

**Changes Added:**
- Import `init_bato_db` from `app.models.bato_models`
- Call `init_bato_db(engine)` in database initialization
- Register `bato_notifications` blueprint
- Register `bato_admin` blueprint
- **REMOVED:** BatoScrapingService initialization (now runs in separate container)

**New Code Sections:**
```python
# Import Bato models
from app.models.bato_models import init_bato_db

# In init_db():
init_bato_db(engine)

# Register blueprints (API access only)
app.register_blueprint(bato_notifications_bp)
app.register_blueprint(bato_admin_bp)
```

**Note:** The BatoScrapingService is no longer started in the main web container. It runs independently in the `bato-scraping-service` container.

---

### `app/repositories/__init__.py` 🔧 MODIFIED
**Purpose:** Repository package initialization

**Changes:**
- Import and export `BatoRepository`

---

## 🗄️ Migration Scripts

### `app/migrations/create_bato_tables_mariadb.py` ✨ NEW
**Purpose:** Creates all Bato tables in MariaDB

**Usage:**
```bash
python app/migrations/create_bato_tables_mariadb.py
```

**Features:**
- Checks for required dependencies (manga_list table)
- Creates all 5 Bato tables
- Handles foreign key relationships
- Idempotent (safe to run multiple times)

---

### `app/migrations/populate_bato_initial_data.py` ✨ NEW
**Purpose:** Populates initial data for all manga with bato_link

**Usage:**
```bash
# Process all manga
doppler run -- python app/migrations/populate_bato_initial_data.py

# Process limited number (for testing)
doppler run -- python app/migrations/populate_bato_initial_data.py --limit 2
```

**Features:**
- Extracts bato_id from bato_link URLs
- Scrapes manga details and chapters
- Creates initial schedules (24h default)
- Creates log entries
- Does NOT create notifications (initial load)
- Continues on errors

---

### `app/migrations/add_is_emitted_to_bato_notifications.py` ✨ NEW
**Purpose:** Adds `is_emitted` column to `bato_notifications` table for polling system

**Usage:**
```bash
doppler run -- python app/migrations/add_is_emitted_to_bato_notifications.py
```

**Features:**
- Adds `is_emitted` BOOLEAN column with DEFAULT FALSE
- Checks if column already exists (idempotent)
- Handles both SQLite and MariaDB/MySQL dialects
- Updates existing rows to set `is_emitted = FALSE`
- Uses transactions for safe migration
- Comprehensive error handling and logging

**Purpose of `is_emitted` Column:**
- Tracks which notifications have been emitted via SocketIO
- Prevents duplicate emissions to users
- Enables polling-based notification delivery
- Required for containerized architecture where Bato service can't directly emit SocketIO events

**Database Changes:**
```sql
-- MariaDB/MySQL
ALTER TABLE bato_notifications 
ADD COLUMN is_emitted BOOLEAN DEFAULT FALSE NOT NULL;

-- SQLite
ALTER TABLE bato_notifications 
ADD COLUMN is_emitted BOOLEAN;
UPDATE bato_notifications 
SET is_emitted = 0 WHERE is_emitted IS NULL;
```

---

## 🧪 Testing

### `app/tests/test_bato_services.py` ✨ NEW
**Purpose:** Unit tests for Bato services

**Test Classes:**
- `TestSchedulingEngine` - Tests schedule calculation logic
- `TestChapterComparator` - Tests new chapter detection
- `TestNotificationManager` - Tests notification creation
- `TestPatternAnalyzer` - Tests pattern detection

**Coverage:**
- Pattern analysis (weekly detection, intervals)
- Schedule calculation (min/max enforcement, status-based)
- Chapter comparison (new vs existing)
- Notification creation (importance levels)

---

### `app/tests/test_bato_integration.py` ✨ NEW
**Purpose:** Integration tests for complete scraping flow

**Test Classes:**
- `TestBatoScrapingService` - Tests end-to-end scraping
- `TestSchedulingEngine` - Tests schedule updates
- `TestNotificationManager` - Tests notification delivery
- `TestPatternAnalyzer` - Tests pattern learning over time

**Features:**
- Mocked GraphQL responses
- Database transaction rollback
- Complete workflow testing

---

### `app/tests/test_bato_service_runner.py` ✨ NEW
**Purpose:** Unit tests for containerized service runner

**Test Classes:**
- `TestBatoServiceRunner` - Tests service runner initialization and lifecycle

**Test Cases:**
- `test_service_runner_initialization` - Verify runner initializes correctly
- `test_database_connection_verification` - Test database connectivity check
- `test_signal_handler_registration` - Verify signal handlers are registered
- `test_graceful_shutdown` - Test shutdown with active jobs
- `test_retry_logic` - Test exponential backoff on failures
- `test_command_line_arguments` - Test --test, --limit, --once flags

**Features:**
- Mocked database connections
- Signal handling verification
- Shutdown timeout testing

---

### Testing the Containerized Setup

#### Local Testing (Without Docker)

```bash
# Test service runner directly
python -m app.services.bato.bato_service_runner --test --limit 5

# Run unit tests
python -m pytest app/tests/test_bato_service_runner.py -v

# Run all Bato tests
python -m pytest app/tests/test_bato*.py -v
```

#### Docker Testing

```bash
# Build image
docker build -t easterntalesshelf:local .

# Test service in container (one-shot)
docker-compose run --rm bato-scraping-service \
  doppler run -- python -m app.services.bato.bato_service_runner --once --limit 3

# Start service and monitor logs
docker-compose up -d bato-scraping-service
docker-compose logs -f bato-scraping-service

# Verify database writes
doppler run -- python check_bato_logs.py

# Stop service
docker-compose stop bato-scraping-service
```

#### Integration Testing

```bash
# Start both containers
docker-compose up -d

# Verify both are running
docker-compose ps

# Check Bato service is scraping
docker-compose logs --tail=50 bato-scraping-service | grep "Scraping job"

# Check web app is polling notifications
docker-compose logs --tail=50 shiro-chan-server | grep -i notification

# Trigger manual scrape via API
curl -X POST http://localhost:5001/api/bato/scrape/12345 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Verify notification appears in database
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
notifications = repo.get_unread_notifications(user_id=1, limit=5)
print(f'Found {len(notifications)} notifications')
"
```

#### Performance Testing

```bash
# Test with many manga
docker-compose run --rm bato-scraping-service \
  doppler run -- python -m app.services.bato.bato_service_runner --test --limit 50

# Monitor resource usage
docker stats bato-scraping-service

# Check scraping duration
docker-compose logs bato-scraping-service | grep "duration" | tail -20
```

---

## 📝 Utility Scripts

### `check_bato_logs.py` ✨ NEW
**Purpose:** Quick script to check Bato scraping logs

**Usage:**
```bash
doppler run -- python check_bato_logs.py
```

**Output:**
- Recent scraping jobs
- Success/failure status
- Chapters found
- Error messages

---

## 📚 Documentation

### `app/services/bato/ERROR_HANDLING.md` ✨ NEW
**Purpose:** Documentation for error handling system

**Contents:**
- Error types and handling strategies
- Retry logic explanation
- Rate limiting documentation
- Usage examples

---

### `app/services/bato/IMPLEMENTATION_SUMMARY.md` ✨ NEW
**Purpose:** Implementation summary for error handling

**Contents:**
- Requirements mapping
- Files created/modified
- Usage examples
- Testing results

---

### `.kiro/specs/bato-notification-system/requirements.md` ✨ NEW
**Purpose:** Complete requirements specification

**Contents:**
- User stories
- Acceptance criteria
- Database schema requirements
- Performance requirements

---

### `.kiro/specs/bato-notification-system/tasks.md` ✨ NEW
**Purpose:** Implementation task list

**Contents:**
- 16 implementation tasks
- Task dependencies
- Completion status
- Requirements mapping

---

### `BATO_REFACTORING_SUMMARY.md` ✨ NEW
**Purpose:** Documents the refactoring of repository and models

**Contents:**
- Files moved
- Import updates
- Verification results

---

### `BATO_RATE_LIMITING.md` ✨ NEW
**Purpose:** Comprehensive guide to rate limiting strategy

**Contents:**
- Sequential vs concurrent scraping explanation
- Randomized delay implementation (4-7 seconds)
- Performance impact analysis
- Configuration options
- Monitoring and troubleshooting
- Best practices for respecting Bato.to API

---

### `IMPORT_VERIFICATION_REPORT.md` ✨ NEW
**Purpose:** Detailed verification of all import updates

**Contents:**
- Complete file list
- Import patterns checked
- Diagnostics results

---

## 📊 Data Files

### `app/scraper/bato_graphql_hidden_api/chapters_list_graphql_output.json` ✨ NEW
**Purpose:** Example output from chapters GraphQL scraper

---

### `app/scraper/bato_graphql_hidden_api/manga_details_graphql_output.json` ✨ NEW
**Purpose:** Example output from manga details GraphQL scraper

---

## 📋 Summary Statistics

### Files Created: 41+
- **Models:** 1 file (5 classes)
- **Repository:** 1 file (1 class, 20+ methods)
- **Scrapers:** 2 files (2 classes)
- **Services:** 9 files (8 classes)
  - 7 in `app/services/bato/` directory
  - 1 in `app/services/` directory (bato_notification_polling.py)
  - 1 service runner (bato_service_runner.py)
- **Blueprints:** 2 files (10+ routes)
- **Templates:** 1 new, 3 modified
- **JavaScript:** 2 new, 1 modified
- **CSS:** 2 modified
- **Migrations:** 3 files
  - create_bato_tables_mariadb.py
  - populate_bato_initial_data.py
  - add_is_emitted_to_bato_notifications.py
- **Tests:** 2 files (120+ test cases)
  - test_bato_services.py
  - test_bato_service_runner.py
- **Documentation:** 8+ files
  - BATO_SYSTEM_COMPONENTS.md
  - BATO_RATE_LIMITING.md
  - BATO_REFACTORING_SUMMARY.md
  - BATO_NOTIFICATION_POLLING.md
  - BATO_SYSTEM_VERIFICATION_REPORT.md
  - ERROR_HANDLING.md
  - IMPLEMENTATION_SUMMARY.md
  - DATABASE_CONNECTION_HANDLING.md
- **Utilities:** 1 file (check_bato_logs.py)
- **Docker:** 1 modified (docker-compose.yml)

### Key Features Implemented:
✅ GraphQL-based scraping (efficient, reliable)  
✅ Intelligent scheduling with pattern analysis  
✅ Real-time notifications via WebSocket  
✅ Comprehensive error handling and retry logic  
✅ Admin dashboard with monitoring  
✅ Complete test coverage  
✅ Thread-safe database operations  
✅ **Human-like rate limiting (4-7s delays, sequential scraping)** 🆕  
✅ Performance monitoring  
✅ Detailed logging system  
✅ **Containerized architecture (separate Bato service container)** 🆕  
✅ **Graceful shutdown with signal handling** 🆕  
✅ **Database polling for notifications** 🆕  
✅ **Standalone service runner** 🆕  

### Architecture Layers:
1. **Database Layer** - Models + Repository
2. **Scraper Layer** - GraphQL API clients
3. **Business Logic** - Services (scheduling, notifications, patterns)
4. **API Layer** - Flask blueprints
5. **Frontend Layer** - Templates + JavaScript
6. **Container Layer** - Docker Compose + Service Runner 🆕
7. **Integration** - App initialization (web app only)

---

## 🔄 System Flow

### Containerized Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bato Service Container                        │
│                                                                  │
│  1. BatoServiceRunner starts                                    │
│     ↓                                                            │
│  2. Verify database connection                                  │
│     ↓                                                            │
│  3. Initialize BatoScrapingService (standalone mode)            │
│     ↓                                                            │
│  4. Run loop (every 5 minutes):                                 │
│     a. Query BatoScrapingSchedule for manga due for scraping    │
│     b. For each manga:                                          │
│        - BatoChaptersListGraphQL.scrape_chapters()              │
│        - BatoMangaDetailsGraphQL.scrape_manga_details()         │
│        - ChapterComparator.find_new_chapters()                  │
│        - If new chapters:                                       │
│          * BatoRepository.bulk_insert_chapters()                │
│          * NotificationManager.create_notification()            │
│          * Write to bato_notifications table                    │
│        - PatternAnalyzer.analyze_release_pattern()              │
│        - SchedulingEngine.calculate_next_scrape_time()          │
│        - BatoRepository.update_schedule_after_scrape()          │
│        - BatoRepository.log_scraping_job()                      │
│     ↓                                                            │
│  5. Sleep 5 minutes, repeat                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Writes to database
                              ↓
                    ┌──────────────────────┐
                    │   Shared Database    │
                    │  - bato_chapters     │
                    │  - bato_notifications│
                    │  - bato_scraper_log  │
                    └──────────────────────┘
                              │
                              │ Polls for new notifications
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Main Web Container                            │
│                                                                  │
│  1. Background task polls bato_notifications (every 30-60s)     │
│     ↓                                                            │
│  2. Find unread notifications                                   │
│     ↓                                                            │
│  3. Emit via SocketIO to connected users                        │
│     ↓                                                            │
│  4. Mark notifications as emitted                               │
│     ↓                                                            │
│  5. Users see notifications in real-time                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Differences from In-Process Architecture

**Before (In-Process):**
- BatoScrapingService ran in main web container
- Direct SocketIO emission from service
- Shared memory space with Flask app

**After (Containerized):**
- BatoScrapingService runs in separate container
- Notifications written to database
- Web app polls database and emits via SocketIO
- Complete isolation between scraping and web serving

---

## 🎯 Entry Points

**For Users:**
- Notifications appear in notification drawer (real-time)
- Admin dashboard at `/admin/bato`

**For Developers:**
- Manual scrape: `POST /api/bato/scrape/<anilist_id>`
- Check logs: `python check_bato_logs.py`
- Test service locally: `python -m app.services.bato.bato_service_runner --test --limit 5`

**For System Admins:**
- Initial setup: `python app/migrations/create_bato_tables_mariadb.py`
- Populate data: `python app/migrations/populate_bato_initial_data.py`
- Monitor: Visit `/admin/bato` dashboard
- Container logs: `docker-compose logs -f bato-scraping-service`

---

## 🚀 Deployment Guide

### Prerequisites

1. **Docker and Docker Compose** installed
2. **Doppler CLI** configured with project token
3. **Database** (MariaDB/MySQL) accessible from Docker network
4. **Base Docker image** built: `easterntalesshelf:local`

### Initial Setup

#### 1. Build Docker Image

```bash
# Build the Docker image
docker build -t easterntalesshelf:local .
```

#### 2. Initialize Database Tables

```bash
# Create Bato tables
doppler run -- python app/migrations/create_bato_tables_mariadb.py

# Populate initial data (optional)
doppler run -- python app/migrations/populate_bato_initial_data.py --limit 10
```

#### 3. Configure Environment Variables

Ensure the following environment variables are set in Doppler:

**Required:**
- `DATABASE_URI` - Database connection string (e.g., `mysql+pymysql://user:pass@host:3306/dbname`)
- `FLASK_ENV` - Environment mode (`production` or `development`)
- `DOPPLER_TOKEN` - Doppler project token for secrets management

**Optional:**
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `BATO_SCRAPE_INTERVAL` - Scraping interval in seconds (default: `300` = 5 minutes)

#### 4. Deploy with Docker Compose

```bash
# Start all services (including Bato service)
docker-compose up -d

# Verify both containers are running
docker-compose ps

# Check Bato service logs
docker-compose logs -f bato-scraping-service
```

### Container Architecture

The system now runs in **two separate containers**:

1. **Main Web Container** (`shiro-chan-server`)
   - Flask web application
   - Gunicorn with gevent workers
   - SocketIO for real-time notifications
   - Bato API endpoints (read-only)
   - Admin dashboard

2. **Bato Scraping Service Container** (`bato-scraping-service`)
   - Standalone Python process
   - BatoScrapingService orchestrator
   - GraphQL scrapers
   - Pattern analyzer and scheduling engine
   - Notification manager (writes to database)

**Communication:**
- Both containers share the same **database** (via Docker networks)
- Both containers share the same **log volume** (`logs_volume:/app/logs`)
- No direct container-to-container communication
- Web app **polls database** for new notifications (every 30-60 seconds)

**Rate Limiting Strategy:**
- Bato service scrapes manga **sequentially** (one at a time)
- **4-7 second randomized delay** between each manga (mimics human behavior)
- Respects Bato.to's hidden GraphQL API by not overwhelming it
- For 300 manga: ~25-35 minutes total per cycle
- Service runs every 5 minutes but only scrapes manga that are "due" per their schedule
- Most manga have 6h-14 day intervals, so not all are scraped each cycle

### Deployment Workflow

#### Standard Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild Docker image
docker build -t easterntalesshelf:local .

# 3. Restart services
docker-compose down
docker-compose up -d

# 4. Verify services started
docker-compose ps
docker-compose logs -f bato-scraping-service
```

#### Rolling Update (Zero Downtime)

```bash
# 1. Update Bato service only
docker-compose up -d --no-deps --build bato-scraping-service

# 2. Update web service only
docker-compose up -d --no-deps --build shiro-chan-server

# 3. Verify both services
docker-compose ps
```

#### Rollback

```bash
# 1. Stop current services
docker-compose down

# 2. Checkout previous version
git checkout <previous-commit>

# 3. Rebuild and restart
docker build -t easterntalesshelf:local .
docker-compose up -d
```

### Monitoring

#### Check Service Status

```bash
# View all containers
docker-compose ps

# Check Bato service logs
docker-compose logs -f bato-scraping-service

# Check web service logs
docker-compose logs -f shiro-chan-server

# Check last 100 lines
docker-compose logs --tail=100 bato-scraping-service
```

#### Check Database Activity

```bash
# Run log checker script
doppler run -- python check_bato_logs.py

# Or query database directly
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
stats = repo.get_scraping_stats(hours=24)
print(stats)
"
```

#### Admin Dashboard

Visit `https://your-domain.com/admin/bato` to view:
- Success/failure rates
- Average scraping duration
- Recent scraping jobs
- Error logs
- Activity charts

### Scaling

#### Horizontal Scaling (Future)

To run multiple Bato service containers:

```yaml
# docker-compose.yml
bato-scraping-service:
  # ... existing config ...
  deploy:
    replicas: 3  # Run 3 instances
```

**Note:** Requires distributed locking (Redis) to prevent duplicate scraping jobs.

#### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
bato-scraping-service:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
```

---

## 🔧 Environment Variables Reference

### Required Variables

| Variable | Description | Example | Used By |
|----------|-------------|---------|---------|
| `DATABASE_URI` | Database connection string | `mysql+pymysql://user:pass@host:3306/db` | Both containers |
| `FLASK_ENV` | Environment mode | `production` or `development` | Both containers |
| `DOPPLER_TOKEN` | Doppler project token | `dp.st.prod.xxxxx` | Both containers |

### Optional Variables

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` | Bato service |
| `BATO_SCRAPE_INTERVAL` | Scraping check interval (seconds) | `300` (5 min) | Bato service |
| `BATO_MIN_DELAY` | Min delay between manga scrapes (seconds) | `4.0` | Bato service |
| `BATO_MAX_DELAY` | Max delay between manga scrapes (seconds) | `7.0` | Bato service |
| `BATO_RETRY_MAX_ATTEMPTS` | Max retry attempts on failure | `3` | Bato service |
| `BATO_RETRY_BACKOFF_FACTOR` | Exponential backoff multiplier | `2` | Bato service |
| `BATO_RATE_LIMIT_DELAY` | Delay when rate limited (seconds) | `60` | Bato service |

### Database Configuration

The `DATABASE_URI` format depends on your database:

**SQLite (Development):**
```bash
DATABASE_URI=sqlite:///anilist_db.db
```

**MariaDB/MySQL (Production):**
```bash
DATABASE_URI=mysql+pymysql://username:password@hostname:3306/database_name?charset=utf8mb4
```

**Connection Pool Settings (Optional):**
```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE=3600
```

### Doppler Configuration

Set up Doppler for secrets management:

```bash
# Install Doppler CLI
# See: https://docs.doppler.com/docs/install-cli

# Login to Doppler
doppler login

# Set up project
doppler setup

# Run commands with Doppler
doppler run -- python app/migrations/create_bato_tables_mariadb.py
doppler run -- docker-compose up -d
```

---

## 🐛 Troubleshooting Guide

### Common Issues

#### 1. Bato Service Container Won't Start

**Symptoms:**
- Container exits immediately after starting
- Error: "Database connection failed"

**Solutions:**

```bash
# Check container logs
docker-compose logs bato-scraping-service

# Verify database connectivity
docker-compose exec bato-scraping-service python -c "
from app.functions.class_mangalist import engine
try:
    conn = engine.connect()
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"

# Check environment variables
docker-compose exec bato-scraping-service env | grep DATABASE_URI

# Restart with fresh logs
docker-compose restart bato-scraping-service
docker-compose logs -f bato-scraping-service
```

#### 2. No Notifications Appearing

**Symptoms:**
- Bato service is running but no notifications in web app
- Chapters are being scraped but users don't see them

**Solutions:**

```bash
# Check if notifications are being created in database
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
notifications = repo.get_unread_notifications(user_id=1, limit=10)
print(f'Found {len(notifications)} unread notifications')
for n in notifications:
    print(f'  - {n.title}')
"

# Check web app polling logs
docker-compose logs shiro-chan-server | grep -i "bato.*notification"

# Verify SocketIO is working
# Open browser console and check for WebSocket connection
```

#### 3. High Error Rate

**Symptoms:**
- Admin dashboard shows >10% error rate
- Many failed scraping jobs in logs

**Solutions:**

```bash
# Check recent errors
doppler run -- python check_bato_logs.py

# Check for rate limiting
docker-compose logs bato-scraping-service | grep -i "rate limit"

# Increase scraping interval to reduce load
# Edit docker-compose.yml:
environment:
  - BATO_SCRAPE_INTERVAL=600  # 10 minutes instead of 5

# Restart service
docker-compose restart bato-scraping-service
```

#### 3a. Rate Limiting / 429 Errors

**Symptoms:**
- Errors mentioning "429" or "rate limit"
- Service pauses for 5 minutes after errors
- Bato.to blocking requests

**Solutions:**

```bash
# Check current delay settings
docker-compose logs bato-scraping-service | grep "Waiting.*before next manga"

# Increase delays between scrapes (more human-like)
# Edit docker-compose.yml:
environment:
  - BATO_MIN_DELAY=6.0  # Increase from 4 to 6 seconds
  - BATO_MAX_DELAY=10.0  # Increase from 7 to 10 seconds

# Restart service
docker-compose restart bato-scraping-service

# Verify new delays are being used
docker-compose logs -f bato-scraping-service | grep "Waiting"
```

**Important Notes:**
- The service scrapes manga **sequentially** (one at a time), not concurrently
- Each manga has a 4-7 second delay before the next one
- For 300 manga, expect ~25-35 minutes per full cycle
- The service only scrapes manga that are "due" based on their schedule
- Most manga won't be scraped every cycle (they have 6h-14 day intervals)

#### 4. "MySQL Server Has Gone Away" Error

**Symptoms:**
- Intermittent database connection errors
- Error: "MySQL server has gone away"

**Solutions:**

```bash
# Increase connection pool recycle time
# Add to Doppler or docker-compose.yml:
DATABASE_POOL_RECYCLE=3600  # Recycle connections every hour

# Increase MySQL wait_timeout
# In MySQL config (my.cnf):
wait_timeout=28800
interactive_timeout=28800

# Restart both services
docker-compose restart
```

#### 5. Service Crashes After Running for Hours

**Symptoms:**
- Service runs fine initially but crashes after several hours
- Memory usage increases over time

**Solutions:**

```bash
# Check memory usage
docker stats bato-scraping-service

# Check for memory leaks in logs
docker-compose logs bato-scraping-service | grep -i "memory"

# Restart service daily (workaround)
# Add to crontab:
0 3 * * * cd /path/to/project && docker-compose restart bato-scraping-service

# Increase memory limit in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 1G
```

#### 6. Scraping Jobs Taking Too Long

**Symptoms:**
- Jobs timeout after 30 seconds
- Many "timeout" errors in logs

**Solutions:**

```bash
# Reduce concurrent workers
# Edit docker-compose.yml:
environment:
  - BATO_MAX_WORKERS=3  # Reduce from 5 to 3

# Check network latency to Bato.to
docker-compose exec bato-scraping-service ping -c 5 bato.to

# Increase timeout (if needed)
# Edit app/services/bato/bato_scraping_service.py:
SCRAPE_TIMEOUT = 60  # Increase from 30 to 60 seconds
```

#### 7. Duplicate Notifications

**Symptoms:**
- Users receive multiple notifications for same chapter
- Database has duplicate notification entries

**Solutions:**

```bash
# Check for duplicate chapter entries
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
repo = BatoRepository()
# Query for duplicates
from sqlalchemy import func
from app.models.bato_models import BatoChapters
duplicates = repo.session.query(
    BatoChapters.bato_chapter_id,
    func.count(BatoChapters.id)
).group_by(BatoChapters.bato_chapter_id).having(func.count(BatoChapters.id) > 1).all()
print(f'Found {len(duplicates)} duplicate chapters')
"

# Clean up duplicates (if found)
# Run migration script to remove duplicates
```

#### 8. Container Restart Loop

**Symptoms:**
- Container keeps restarting every few seconds
- `docker-compose ps` shows "Restarting"

**Solutions:**

```bash
# Check exit code
docker-compose ps

# View full logs
docker-compose logs --tail=200 bato-scraping-service

# Disable auto-restart temporarily for debugging
# Edit docker-compose.yml:
restart: "no"  # Change from "always"

# Start manually to see error
docker-compose up bato-scraping-service

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Python import errors
# - Permission issues with log directory
```

### Debug Mode

Run the service in debug mode for detailed logging:

```bash
# Stop the container
docker-compose stop bato-scraping-service

# Run manually with debug flags
docker-compose run --rm bato-scraping-service \
  doppler run -- python -m app.services.bato.bato_service_runner --test --limit 5

# Or set LOG_LEVEL to DEBUG
docker-compose run --rm -e LOG_LEVEL=DEBUG bato-scraping-service \
  doppler run -- python -m app.services.bato.bato_service_runner
```

### Health Checks

Add health check to `docker-compose.yml`:

```yaml
bato-scraping-service:
  # ... existing config ...
  healthcheck:
    test: ["CMD", "python", "-c", "from app.functions.class_mangalist import engine; engine.connect()"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

### Log Analysis

Useful log analysis commands:

```bash
# Count errors in last hour
docker-compose logs --since 1h bato-scraping-service | grep -i error | wc -l

# Find most common errors
docker-compose logs bato-scraping-service | grep ERROR | sort | uniq -c | sort -rn | head -10

# Check scraping success rate
docker-compose logs bato-scraping-service | grep "Scraping job completed" | wc -l
docker-compose logs bato-scraping-service | grep "Scraping job failed" | wc -l

# Monitor in real-time
docker-compose logs -f bato-scraping-service | grep -E "(ERROR|WARNING|Scraping job)"
```

### Performance Tuning

#### Optimize Database Queries

```bash
# Enable query logging
# Add to docker-compose.yml:
environment:
  - SQLALCHEMY_ECHO=true  # Log all SQL queries

# Analyze slow queries
docker-compose logs bato-scraping-service | grep "SELECT" | grep -E "[0-9]+\.[0-9]+s"
```

#### Optimize Scraping Schedule

```bash
# Check schedule distribution
doppler run -- python -c "
from app.database_module.bato_repository import BatoRepository
from datetime import datetime, timedelta
repo = BatoRepository()
now = datetime.now()
next_hour = now + timedelta(hours=1)
schedules = repo.session.query(BatoScrapingSchedule).filter(
    BatoScrapingSchedule.next_scrape_time.between(now, next_hour)
).count()
print(f'{schedules} manga scheduled in next hour')
"

# Spread out schedules if too many at once
# Run schedule optimizer script (if available)
```

### Getting Help

If issues persist:

1. **Check logs:** `docker-compose logs -f bato-scraping-service`
2. **Check admin dashboard:** Visit `/admin/bato` for statistics
3. **Run diagnostics:** `doppler run -- python check_bato_logs.py`
4. **Check database:** Verify tables exist and have data
5. **Test manually:** Run service with `--test --limit 1` flags
6. **Review requirements:** Check `.kiro/specs/bato-containerization/requirements.md`

---

## 📊 Monitoring and Observability

### Key Metrics to Monitor

1. **Scraping Success Rate**
   - Target: >95%
   - Check: Admin dashboard or `check_bato_logs.py`

2. **Average Scraping Duration**
   - Target: <10 seconds per manga
   - Check: Admin dashboard performance metrics

3. **Error Rate**
   - Target: <5%
   - Check: Admin dashboard or logs

4. **Notification Delivery**
   - Target: <60 seconds from scrape to user notification
   - Check: Compare scraper log timestamps with notification timestamps

5. **Container Health**
   - Target: 99.9% uptime
   - Check: `docker-compose ps` and container restart count

### Log Files

All logs are written to `logs/bato/` directory:

- `bato.log` - General operations (INFO level)
- `bato_errors.log` - Errors only (ERROR level)
- `bato_performance.log` - Performance metrics

**Log Rotation:**
- Max size: 10MB per file
- Max files: 5 (50MB total)
- Automatic rotation by Python logging

### Alerting

Set up alerts for:

- Container restart (indicates crash)
- Error rate >10% over 1 hour
- No scraping jobs completed in 30 minutes
- Database connection failures
- Disk space <10% (for logs)

Example monitoring script:

```bash
#!/bin/bash
# monitor_bato.sh

# Check if container is running
if ! docker-compose ps | grep -q "bato-scraping-service.*Up"; then
    echo "ALERT: Bato service container is down!"
    # Send alert (email, Slack, etc.)
fi

# Check error rate
ERROR_COUNT=$(docker-compose logs --since 1h bato-scraping-service | grep -i error | wc -l)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "ALERT: High error rate: $ERROR_COUNT errors in last hour"
fi

# Check last scraping job
LAST_JOB=$(docker-compose logs --since 30m bato-scraping-service | grep "Scraping job completed" | tail -1)
if [ -z "$LAST_JOB" ]; then
    echo "ALERT: No scraping jobs completed in last 30 minutes"
fi
```

Run this script via cron every 15 minutes:

```bash
*/15 * * * * /path/to/monitor_bato.sh
```
