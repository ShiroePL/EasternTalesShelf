# Error Handling and Logging - Bato Notification System

This document describes the comprehensive error handling and logging system implemented for the Bato notification system.

## Overview

The error handling system provides:
- **Network error retry logic** with exponential backoff
- **GraphQL error handling** with detailed logging
- **Rate limiting detection** (429 responses) with automatic pause
- **Database error handling** for duplicates, foreign keys, and deadlocks
- **Pattern analysis fallbacks** for insufficient data
- **Comprehensive logging** for debugging and monitoring
- **Performance tracking** with alerts for slow operations
- **Error rate monitoring** with automatic alerts

## Components

### 1. Error Handler (`error_handler.py`)

Central error handling module with custom exception types and decorators.

#### Exception Types

- `BatoError`: Base exception for all Bato errors
- `NetworkError`: Network-related errors (connection, timeout)
- `GraphQLError`: GraphQL API errors
- `RateLimitError`: Rate limiting errors (429 responses)
- `DatabaseError`: Database operation errors
- `PatternAnalysisError`: Pattern analysis errors

#### Decorators

**`@with_retry`**: Automatic retry with exponential backoff
```python
@with_retry(max_attempts=3, initial_delay=1.0)
def scrape_chapters(manga_id):
    return api.get_chapters(manga_id)
```

**`@with_database_retry`**: Database-specific retry for deadlocks
```python
@with_database_retry(max_attempts=3)
def insert_chapters(chapters):
    db_session.bulk_insert_mappings(BatoChapters, chapters)
    db_session.commit()
```

**`@log_performance`**: Performance tracking with alerts
```python
@log_performance("scrape_chapters")
def scrape_chapters(manga_id):
    return api.get_chapters(manga_id)
```

#### Rate Limiting

The error handler maintains global rate limit state:

```python
# Check if rate limited
if ErrorHandler.is_rate_limited():
    # Skip operation
    return

# Set rate limit (e.g., after 429 response)
ErrorHandler.set_rate_limit(300)  # 5 minutes

# Get rate limit info
info = ErrorHandler.get_rate_limit_info()
# Returns: {'is_limited': True, 'remaining_seconds': 245, ...}
```

### 2. Logging Configuration (`logging_config.py`)

Comprehensive logging setup with multiple log files.

#### Log Files

- **`bato.log`**: General operations (rotating, 10MB, 5 backups)
- **`bato_errors.log`**: Errors only (rotating, 5MB, 3 backups)
- **`bato_performance.log`**: Performance metrics (rotating, 5MB, 3 backups)

#### Usage

```python
from app.services.bato.logging_config import init_logging, get_bato_logger

# Initialize at startup
init_logging(log_level='INFO', log_to_file=True)

# Get logger in modules
logger = get_bato_logger('scraper')
logger.info("Starting scraping job")
```

#### Structured Logging

```python
from app.services.bato.logging_config import log_scraping_metrics

log_scraping_metrics(
    manga_name="One Piece",
    duration=1.5,
    chapters_found=100,
    new_chapters=2,
    success=True
)
```

### 3. Error Monitor (`error_monitor.py`)

Tracks errors and performance metrics with automatic alerts.

#### Features

- **Error Rate Monitoring**: Alerts when errors exceed 10% over 24 hours
- **Performance Tracking**: Logs operations exceeding 2 seconds
- **Health Status**: Overall system health assessment
- **Sliding Window**: Maintains recent events in memory

#### Usage

```python
from app.services.bato.error_monitor import record_error, record_performance, get_monitor

# Record errors
record_error(
    error_type='network',
    error_message='Connection timeout',
    manga_id=12345,
    duration_seconds=15.0
)

# Record performance
record_performance(
    operation='scrape_chapters',
    duration_seconds=1.8,
    manga_id=12345
)

# Get summaries
monitor = get_monitor()
error_summary = monitor.get_error_summary(hours=24)
perf_summary = monitor.get_performance_summary(hours=24)
health = monitor.get_health_status()
```

## Error Handling Patterns

### Network Errors

Network errors are automatically retried with exponential backoff:

```python
# In bato_scraping_service.py
try:
    chapters_data = self.chapters_scraper.scrape_chapters(bato_id)
except Exception as e:
    if '429' in str(e) or 'rate limit' in str(e).lower():
        ErrorHandler.set_rate_limit(300)  # 5 minutes
        raise RateLimitError(f"Rate limited: {e}")
    raise NetworkError(f"Failed to scrape: {e}")
```

### GraphQL Errors

GraphQL errors are logged with full context:

```python
# In bato_chapters_list_graphql.py
if 'errors' in data:
    errors = data['errors']
    error_msg = errors[0].get('message', 'Unknown error')
    
    logger.error(
        f"GraphQL error: {error_msg}",
        extra={
            'query_variables': variables,
            'all_errors': errors
        }
    )
    raise Exception(f"GraphQL error: {error_msg}")
```

### Database Errors

Database errors are handled with specific logic:

```python
# In bato_repository.py
try:
    db_session.commit()
except IntegrityError as e:
    if 'duplicate' in str(e).lower():
        logger.debug("Duplicate key, ignoring (expected)")
        return None
    elif 'foreign key' in str(e).lower():
        logger.error(f"Foreign key violation: {e}")
        raise
except OperationalError as e:
    if 'deadlock' in str(e).lower():
        logger.warning("Deadlock detected, retrying...")
        # Retry with random delay
        time.sleep(random.uniform(0.1, 0.5))
        # Retry logic...
```

### Pattern Analysis Fallbacks

Pattern analysis gracefully handles insufficient data:

```python
# In pattern_analyzer.py
def calculate_average_interval(self, chapter_dates):
    if not chapter_dates or len(chapter_dates) < 2:
        logger.debug("Insufficient data, returning None as fallback")
        return None
    
    try:
        # Calculate interval...
    except Exception as e:
        logger.error(f"Error calculating interval: {e}. Using fallback.")
        return None  # Fallback to default
```

## Monitoring and Alerts

### Error Rate Alerts

Automatically triggered when error rate exceeds 10% over 24 hours:

```
[2024-01-15 10:30:00] WARNING HIGH ERROR RATE DETECTED: 12.5% over 24h 
(25 errors, threshold: 10.0%)
```

### Performance Alerts

Logged when operations exceed 2 seconds:

```
[2024-01-15 10:30:00] WARNING Slow operation detected: scrape_chapters 
took 3.45s (threshold: 2.0s)
```

### Rate Limit Alerts

Logged when rate limiting is detected:

```
[2024-01-15 10:30:00] WARNING RATE_LIMITED | Pausing for 300s | 
Rate limit count: 1
```

## Best Practices

### 1. Always Use Try-Except

Wrap all external calls in try-except blocks:

```python
try:
    result = external_api_call()
except Exception as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    raise
```

### 2. Log Context Information

Include relevant context in log messages:

```python
logger.error(
    f"Failed to scrape manga {manga_id}: {error}",
    extra={
        'manga_id': manga_id,
        'bato_id': bato_id,
        'attempt': attempt_number
    }
)
```

### 3. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (recoverable issues)
- **ERROR**: Error messages (operation failed)
- **CRITICAL**: Critical errors (system failure)

### 4. Handle Rate Limiting Proactively

Check rate limit status before operations:

```python
if ErrorHandler.is_rate_limited():
    logger.warning("Rate limited, skipping operation")
    return False
```

### 5. Record Metrics

Always record performance and error metrics:

```python
start_time = time.time()
try:
    result = operation()
    duration = time.time() - start_time
    record_performance('operation', duration)
    record_success()
except Exception as e:
    duration = time.time() - start_time
    record_error('operation_type', str(e), duration_seconds=duration)
    raise
```

## Testing Error Handling

### Simulate Network Errors

```python
# Mock network timeout
with patch('requests.Session.post') as mock_post:
    mock_post.side_effect = requests.exceptions.Timeout()
    # Test retry logic...
```

### Simulate Rate Limiting

```python
# Mock 429 response
response = Mock()
response.status_code = 429
response.headers = {'Retry-After': '300'}
# Test rate limit handling...
```

### Simulate Database Errors

```python
# Mock deadlock
with patch('db_session.commit') as mock_commit:
    mock_commit.side_effect = OperationalError('deadlock detected')
    # Test retry logic...
```

## Configuration

### Environment Variables

```bash
# Logging level
BATO_LOG_LEVEL=INFO

# Enable file logging
BATO_LOG_TO_FILE=true

# Log directory
BATO_LOG_DIR=logs/bato
```

### Service Configuration

```python
# In bato_scraping_service.py
MAX_RETRY_ATTEMPTS = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 60  # seconds
```

## Troubleshooting

### High Error Rate

1. Check error summary: `monitor.get_error_summary(hours=24)`
2. Review error types: Look at `errors_by_type`
3. Check recent errors: Review `recent_errors` list
4. Investigate common patterns

### Slow Operations

1. Check performance summary: `monitor.get_performance_summary(hours=24)`
2. Identify slow operations: Look at `operations_by_type`
3. Review slow operation rate
4. Optimize slow operations

### Rate Limiting

1. Check rate limit status: `ErrorHandler.get_rate_limit_info()`
2. Review rate limit count
3. Adjust scraping frequency if needed
4. Consider implementing backoff strategy

## Requirements Mapping

This error handling system fulfills the following requirements:

- **5.5**: Network error retry logic in scraping service ✓
- **5.5**: GraphQL error handling with appropriate logging ✓
- **5.5**: Rate limiting detection (429 responses) with 5-minute pause ✓
- **5.5**: Database error handling (duplicate key, foreign key, deadlock) ✓
- **5.5**: Pattern analysis fallbacks for insufficient data ✓
- **10.1**: Record duration_seconds in bato_scraper_log ✓
- **10.2**: Record chapters_found and new_chapters counts ✓
- **10.4**: Log warning when errors exceed 10% over 24 hours ✓
- **10.5**: Track API response times and log when they exceed 2 seconds ✓
