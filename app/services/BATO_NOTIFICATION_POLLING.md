# Bato Notification Polling System

## Overview

The Bato notification polling system bridges the gap between the standalone Bato scraping container and the main web application's real-time notification system. Since the Bato scraping service runs in a separate Docker container, it cannot directly emit SocketIO notifications to connected clients. Instead, it writes notifications to the database, and the web application polls for new notifications and emits them.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Bato Scraping Container                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  BatoScrapingService                               │     │
│  │  - Scrapes manga chapters                          │     │
│  │  - Detects new chapters                            │     │
│  │  - Writes to bato_notifications table              │     │
│  │    (is_emitted = FALSE)                            │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Database writes
                          ▼
              ┌────────────────────────┐
              │  bato_notifications    │
              │  table                 │
              │  - id                  │
              │  - manga_name          │
              │  - message             │
              │  - is_read = FALSE     │
              │  - is_emitted = FALSE  │
              └────────────────────────┘
                          │
                          │ Polling (every 60s)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Main Web Application                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │  BatoNotificationPoller                            │     │
│  │  - Polls database every 60 seconds                 │     │
│  │  - Fetches notifications where is_emitted = FALSE  │     │
│  │  - Emits via SocketIO to all clients               │     │
│  │  - Marks notifications as emitted                  │     │
│  │    (is_emitted = TRUE)                             │     │
│  └────────────────────────────────────────────────────┘     │
│                          │                                   │
│                          │ SocketIO emit                     │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Connected Clients (Browsers)                      │     │
│  │  - Receive real-time notifications                 │     │
│  │  - Display toast/popup                             │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. BatoNotificationPoller (`app/services/bato_notification_polling.py`)

The main polling service that runs in a background thread.

**Key Features:**
- Polls database every 60 seconds (configurable)
- Fetches unemitted notifications
- Emits via SocketIO with event name `bato_notification`
- Marks notifications as emitted to avoid duplicates
- Comprehensive error handling and logging

**Lifecycle:**
- Started automatically when Flask app initializes
- Runs in daemon thread (won't block app shutdown)
- Gracefully stops when app shuts down

### 2. BatoRepository Methods

**`get_unemitted_notifications(limit=100)`**
- Queries `bato_notifications` table
- Filters by `is_emitted = FALSE`
- Orders by importance and creation time
- Returns list of BatoNotifications objects

**`mark_notifications_emitted(notification_ids)`**
- Bulk updates notifications
- Sets `is_emitted = TRUE`
- Prevents duplicate emissions

### 3. Database Schema Addition

**New Column: `is_emitted`**
- Type: BOOLEAN
- Default: FALSE
- Purpose: Track which notifications have been emitted via SocketIO

## Configuration

### Poll Interval

The polling interval can be configured when initializing the poller:

```python
# In app.py
init_bato_notification_poller(socketio, poll_interval=60)  # 60 seconds
```

**Considerations:**
- Lower interval = more real-time, but more database queries
- Higher interval = less database load, but delayed notifications
- Recommended: 60 seconds (1 minute) for good balance

### SocketIO Event

Notifications are emitted with the event name `bato_notification`:

```javascript
// Frontend JavaScript
socket.on('bato_notification', function(data) {
    console.log('New Bato notification:', data);
    // Display toast/popup
    showNotification(data.manga_name, data.message);
});
```

## Notification Data Format

Each emitted notification contains:

```json
{
    "id": 123,
    "anilist_id": 456,
    "bato_link": "https://batotwo.com/title/12345-manga-name",
    "notification_type": "new_chapter",
    "manga_name": "My Favorite Manga",
    "message": "New chapter 112 available!",
    "chapter_dname": "Chapter 112",
    "chapter_full_url": "https://batotwo.com/chapter/789",
    "old_status": null,
    "new_status": null,
    "chapters_count": 1,
    "importance": 1,
    "is_read": false,
    "created_at": "2024-01-15T10:30:00",
    "source": "bato"
}
```

## Error Handling

The poller includes comprehensive error handling:

1. **Database Connection Errors**
   - Logged with full traceback
   - Service continues running
   - Next poll attempt in 60 seconds

2. **SocketIO Emission Errors**
   - Individual notification errors logged
   - Other notifications still processed
   - Failed notifications remain unemitted

3. **Marking Errors**
   - Logged but doesn't stop service
   - Notifications may be re-emitted on next poll
   - Idempotent on frontend (same notification ID)

## Monitoring

### Logs

The poller logs important events:

```
INFO: BatoNotificationPoller initialized with 60s interval
INFO: BatoNotificationPoller started
INFO: Found 3 new Bato notifications to emit
DEBUG: Emitted notification 123: new_chapter for My Favorite Manga
INFO: Marked 3 notifications as emitted
```

### Health Checks

Check if poller is running:

```python
from app.services.bato_notification_polling import get_poller_instance

poller = get_poller_instance()
if poller and poller.running:
    print("Poller is running")
else:
    print("Poller is not running")
```

## Testing

### Manual Testing

1. **Create a test notification:**
   ```python
   from app.database_module.bato_repository import BatoRepository
   
   BatoRepository.create_notification({
       'anilist_id': 123,
       'bato_link': 'https://batotwo.com/title/12345',
       'notification_type': 'new_chapter',
       'manga_name': 'Test Manga',
       'message': 'Test notification',
       'is_emitted': False
   })
   ```

2. **Wait 60 seconds** (or trigger manually)

3. **Check frontend** for SocketIO event

4. **Verify database** - `is_emitted` should be TRUE

### Integration Testing

See `app/tests/test_bato_notification_polling.py` for automated tests.

## Deployment

### Development

The poller starts automatically when running the Flask app:

```bash
python app/app.py
```

### Production (Docker)

The poller is initialized in `app.py` after SocketIO setup:

```python
# Initialize SocketIO
socketio = SocketIO(app, ...)

# Initialize Bato notification poller
init_bato_notification_poller(socketio, poll_interval=60)
```

No additional configuration needed - it runs in the main web container.

## Troubleshooting

### Notifications not appearing

1. **Check poller is running:**
   ```python
   from app.services.bato_notification_polling import get_poller_instance
   print(get_poller_instance().running)
   ```

2. **Check database:**
   ```sql
   SELECT * FROM bato_notifications WHERE is_emitted = FALSE;
   ```

3. **Check logs:**
   ```bash
   grep "BatoNotificationPoller" logs/app.log
   ```

### Duplicate notifications

- Should not happen due to `is_emitted` flag
- If it does, check database for notifications with `is_emitted = TRUE` being re-emitted
- May indicate database transaction issues

### High database load

- Increase poll interval (e.g., 120 seconds)
- Add database index on `is_emitted` column
- Consider using database triggers (more complex)

## Future Enhancements

1. **Database Triggers**: Use database triggers to push notifications instead of polling
2. **Redis Pub/Sub**: Use Redis for real-time notification delivery
3. **WebSocket Direct**: Allow Bato container to emit directly via Redis adapter
4. **Batch Processing**: Process notifications in larger batches for efficiency
5. **Priority Queue**: Prioritize important notifications (status changes, batch updates)

## Requirements Satisfied

This implementation satisfies **Requirement 1.5** from the containerization spec:

> WHEN both containers are running, THE containers SHALL share access to the same database through the Docker network

The notification polling system enables communication between containers via the shared database, maintaining the separation of concerns while providing real-time notifications to users.
