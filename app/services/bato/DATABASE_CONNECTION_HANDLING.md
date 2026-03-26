# Database Connection Handling for Bato Service

## Overview

The Bato service uses a robust database connection handling system designed for standalone containerized deployment. This system provides connection pooling, automatic retry logic, and comprehensive error handling.

## Components

### 1. DatabaseConnectionHandler (`database_connection_handler.py`)

The main class that manages database connections for the standalone Bato service.

**Features:**
- Connection pooling with configurable pool size
- Pre-ping to test connections before use
- Automatic connection recycling
- Thread-safe session management
- Retry logic with exponential backoff
- "MySQL server has gone away" error handling

**Configuration:**
```python
POOL_SIZE = 10              # Number of connections to maintain
MAX_OVERFLOW = 5            # Additional connections when pool is full
POOL_RECYCLE = 3600         # Recycle connections after 1 hour
POOL_PRE_PING = True        # Test connections before using
POOL_TIMEOUT = 30           # Timeout for getting connection from pool
MAX_RETRIES = 5             # Maximum retry attempts
INITIAL_RETRY_DELAY = 1     # Initial delay before retry (seconds)
MAX_RETRY_DELAY = 30        # Maximum delay between retries (seconds)
```

### 2. Repository Decorator (`bato_repository.py`)

The `@handle_db_connection_errors` decorator provides automatic retry logic for repository methods.

**Features:**
- Automatic retry on connection errors
- Exponential backoff
- Connection pool disposal on "server has gone away"
- Configurable retry attempts and delays

## Usage

### In Service Runner

```python
from app.services.bato.database_connection_handler import (
    initialize_db_handler,
    get_db_handler,
    dispose_db_handler
)

# Initialize at startup
if not initialize_db_handler():
    logger.error("Failed to initialize database handler")
    sys.exit(1)

# Get handler instance
db_handler = get_db_handler()

# Verify connection
if not db_handler.verify_connection():
    logger.error("Database connection verification failed")
    sys.exit(1)

# Check pool status
pool_status = db_handler.get_pool_status()
logger.info(f"Connection pool: {pool_status}")

# Cleanup at shutdown
dispose_db_handler()
```

### In Repository Methods

```python
@handle_db_connection_errors(max_retries=3)
def get_manga_details(anilist_id: int) -> Optional[BatoMangaDetails]:
    """Method with automatic retry on connection errors."""
    try:
        details = db_session.query(BatoMangaDetails).filter(
            BatoMangaDetails.anilist_id == anilist_id
        ).first()
        return details
    except Exception as e:
        logger.error(f"Error: {e}")
        db_session.rollback()
        return None
    finally:
        db_session.remove()
```

### Using Context Manager

```python
# For custom database operations
with db_handler.get_session() as session:
    result = session.execute(text("SELECT * FROM table"))
    # Session automatically commits on success
    # Session automatically rolls back on error
```

## Error Handling

### Connection Errors Handled

The system automatically handles and retries these errors:

1. **"MySQL server has gone away"**
   - Disposes connection pool
   - Retries with exponential backoff
   - Logs connection loss

2. **"Lost connection to MySQL server"**
   - Disposes connection pool
   - Retries operation
   - Logs connection loss

3. **"Connection was killed"**
   - Retries operation
   - Logs error

4. **"Can't connect to MySQL server"**
   - Retries with backoff
   - Logs connection failure

5. **"Connection refused"**
   - Retries with backoff
   - Logs connection failure

6. **Deadlock errors**
   - Retries with random delay
   - Logs deadlock occurrence

### Retry Logic

**Exponential Backoff:**
```
Attempt 1: 1 second delay
Attempt 2: 2 seconds delay
Attempt 3: 4 seconds delay
Attempt 4: 8 seconds delay
Attempt 5: 16 seconds delay (capped at MAX_RETRY_DELAY)
```

**Connection Pool Disposal:**
When "server has gone away" or "lost connection" errors occur, the connection pool is disposed to force new connections on the next attempt.

## Monitoring

### Pool Status

Get current connection pool status:

```python
pool_status = db_handler.get_pool_status()
# Returns:
# {
#     'initialized': True,
#     'pool_size': 10,
#     'checked_in': 8,      # Available connections
#     'checked_out': 2,     # In-use connections
#     'overflow': 0,        # Extra connections created
#     'total_connections': 10
# }
```

### Logging

The system logs:
- Connection initialization
- Connection verification attempts
- Connection errors and retries
- Pool disposal events
- Retry delays and attempts

**Log Levels:**
- `INFO`: Normal operations (initialization, verification)
- `WARNING`: Retry attempts, connection issues
- `ERROR`: Failed operations, max retries reached
- `CRITICAL`: Fatal errors preventing startup

## Requirements Satisfied

### Requirement 3.1: DATABASE_URI Configuration
✓ Uses `DATABASE_URI` from `app.config` (Doppler-managed)

### Requirement 3.2: Doppler Secret Management
✓ Secrets loaded via Doppler in `app.config`

### Requirement 3.4: Independent Connection Pooling
✓ Separate connection pool with configurable settings
✓ Pool size: 10 connections
✓ Max overflow: 5 additional connections
✓ Pool recycle: 3600 seconds (1 hour)
✓ Pre-ping enabled for connection testing

### Requirement 3.5: Retry Logic with Exponential Backoff
✓ Maximum 5 retry attempts
✓ Exponential backoff (1s → 2s → 4s → 8s → 16s)
✓ Handles "MySQL server has gone away" errors
✓ Automatic connection pool disposal on connection loss

### Requirement 5.3: Database Error Handling
✓ Comprehensive error handling in repository methods
✓ Automatic retry on transient errors
✓ Proper rollback on failures
✓ Session cleanup in finally blocks

## Testing

### Manual Testing

Run the test script:
```bash
python test_db_connection_handler.py
```

### Integration Testing

Test with the service runner:
```bash
python -m app.services.bato.bato_service_runner --test --once
```

### Verify Connection Pool

Check pool status in logs:
```
Connection pool: size=10, max_overflow=5, recycle=3600s
Pool status: {'initialized': True, 'pool_size': 10, ...}
```

## Troubleshooting

### Connection Pool Exhausted

**Symptom:** "QueuePool limit of size X overflow Y reached"

**Solution:**
- Increase `POOL_SIZE` or `MAX_OVERFLOW`
- Check for connection leaks (missing `db_session.remove()`)
- Reduce concurrent operations

### Frequent "Server Has Gone Away" Errors

**Symptom:** Repeated connection loss errors

**Possible Causes:**
1. MySQL `wait_timeout` too low
2. Network instability
3. Database server restarts

**Solutions:**
1. Increase MySQL `wait_timeout` setting
2. Reduce `POOL_RECYCLE` time (currently 3600s)
3. Enable `POOL_PRE_PING` (already enabled)

### Slow Connection Verification

**Symptom:** Long startup time

**Solution:**
- Check network connectivity to database
- Verify database server is responsive
- Check firewall rules

### Max Retries Reached

**Symptom:** "Failed after 5 retries"

**Possible Causes:**
1. Database server down
2. Network issues
3. Invalid credentials

**Solutions:**
1. Verify database server is running
2. Check network connectivity
3. Verify DATABASE_URI is correct
4. Check Doppler secrets are loaded

## Best Practices

1. **Always use context managers** for custom queries:
   ```python
   with db_handler.get_session() as session:
       # Your code here
   ```

2. **Apply decorator to repository methods** that interact with database:
   ```python
   @handle_db_connection_errors(max_retries=3)
   def your_method():
       # Your code here
   ```

3. **Always cleanup** in finally blocks:
   ```python
   try:
       # Database operations
   finally:
       db_session.remove()
   ```

4. **Monitor pool status** regularly:
   ```python
   pool_status = db_handler.get_pool_status()
   logger.info(f"Pool: {pool_status}")
   ```

5. **Dispose handler** on shutdown:
   ```python
   dispose_db_handler()
   ```

## Performance Considerations

### Connection Pool Sizing

**Current Settings:**
- Pool size: 10 connections
- Max overflow: 5 connections
- Total possible: 15 connections

**Recommendations:**
- For light load: 5-10 connections sufficient
- For heavy load: Increase to 20-30 connections
- Monitor `checked_out` to determine if pool is adequate

### Connection Recycling

**Current Setting:** 3600 seconds (1 hour)

**Considerations:**
- MySQL default `wait_timeout`: 28800 seconds (8 hours)
- Recycling prevents stale connections
- Lower value = more connection overhead
- Higher value = risk of timeout errors

### Pre-Ping Overhead

**Current Setting:** Enabled

**Impact:**
- Small overhead on each connection checkout
- Prevents "server has gone away" errors
- Recommended for production use

## Security

### Credential Management

✓ All credentials managed via Doppler
✓ No hardcoded passwords
✓ DATABASE_URI masked in logs

### Connection Security

✓ Connection timeout: 10 seconds
✓ Pool timeout: 30 seconds
✓ Automatic cleanup on errors

## Future Enhancements

Potential improvements:

1. **Health Check Endpoint**
   - HTTP endpoint for Docker health checks
   - Returns connection pool status

2. **Metrics Export**
   - Export pool metrics to Prometheus
   - Track connection usage over time

3. **Dynamic Pool Sizing**
   - Adjust pool size based on load
   - Scale up during peak times

4. **Connection Warmup**
   - Pre-create connections on startup
   - Reduce initial latency

5. **Circuit Breaker**
   - Stop retrying after repeated failures
   - Prevent cascading failures
