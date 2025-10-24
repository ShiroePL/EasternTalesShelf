"""
Error Handler - Centralized Error Handling for Bato Notification System

Provides comprehensive error handling for:
- Network errors with retry logic
- GraphQL errors with appropriate logging
- Rate limiting detection (429 responses)
- Database errors (duplicate key, foreign key, deadlock)
- Pattern analysis fallbacks

Requirements:
- 5.5: Network error retry logic in scraping service
- 10.1, 10.2, 10.5: Comprehensive logging for debugging and monitoring
"""

import logging
import time
from typing import Optional, Callable, Any, Dict
from functools import wraps
from datetime import datetime, timedelta
import requests
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError

logger = logging.getLogger(__name__)


class BatoError(Exception):
    """Base exception for Bato notification system errors."""
    pass


class NetworkError(BatoError):
    """Network-related errors (connection, timeout, etc.)."""
    pass


class GraphQLError(BatoError):
    """GraphQL API errors."""
    pass


class RateLimitError(BatoError):
    """Rate limiting errors (429 responses)."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after or 300  # Default 5 minutes


class DatabaseError(BatoError):
    """Database operation errors."""
    pass


class PatternAnalysisError(BatoError):
    """Pattern analysis errors."""
    pass


class ErrorHandler:
    """
    Centralized error handling with retry logic and logging.
    
    This class provides decorators and utility methods for handling
    various types of errors throughout the Bato notification system.
    """
    
    # Rate limiting state
    _rate_limit_until: Optional[datetime] = None
    _rate_limit_count: int = 0
    
    @staticmethod
    def is_rate_limited() -> bool:
        """
        Check if we're currently rate limited.
        
        Returns:
            True if rate limited, False otherwise
        """
        if ErrorHandler._rate_limit_until is None:
            return False
        
        if datetime.now() < ErrorHandler._rate_limit_until:
            return True
        
        # Rate limit expired, reset
        ErrorHandler._rate_limit_until = None
        ErrorHandler._rate_limit_count = 0
        return False
    
    @staticmethod
    def set_rate_limit(duration_seconds: int = 300):
        """
        Set rate limit for specified duration.
        
        Requirement 5.5: Implement rate limiting detection with 5-minute pause
        
        Args:
            duration_seconds: How long to pause (default 5 minutes)
        """
        ErrorHandler._rate_limit_until = datetime.now() + timedelta(seconds=duration_seconds)
        ErrorHandler._rate_limit_count += 1
        
        logger.warning(
            f"Rate limit activated for {duration_seconds}s "
            f"(count: {ErrorHandler._rate_limit_count}, "
            f"until: {ErrorHandler._rate_limit_until.strftime('%H:%M:%S')})"
        )
    
    @staticmethod
    def get_rate_limit_info() -> Dict:
        """
        Get current rate limit information.
        
        Returns:
            Dictionary with rate limit status
        """
        if ErrorHandler._rate_limit_until is None:
            return {
                'is_limited': False,
                'count': ErrorHandler._rate_limit_count
            }
        
        remaining = (ErrorHandler._rate_limit_until - datetime.now()).total_seconds()
        return {
            'is_limited': remaining > 0,
            'remaining_seconds': max(0, int(remaining)),
            'until': ErrorHandler._rate_limit_until.isoformat(),
            'count': ErrorHandler._rate_limit_count
        }
    
    @staticmethod
    def handle_network_error(error: Exception, context: str = "") -> NetworkError:
        """
        Handle network-related errors with appropriate logging.
        
        Requirement 5.5: Network error retry logic
        
        Args:
            error: Original exception
            context: Context information for logging
            
        Returns:
            NetworkError with detailed message
        """
        error_msg = str(error)
        
        # Check for rate limiting (429)
        if isinstance(error, requests.exceptions.HTTPError):
            if error.response.status_code == 429:
                retry_after = error.response.headers.get('Retry-After', 300)
                try:
                    retry_after = int(retry_after)
                except:
                    retry_after = 300
                
                logger.error(
                    f"Rate limit detected (429): {context}. "
                    f"Pausing for {retry_after}s"
                )
                ErrorHandler.set_rate_limit(retry_after)
                raise RateLimitError(
                    f"Rate limited: {context}",
                    retry_after=retry_after
                )
        
        # Log network errors
        if isinstance(error, requests.exceptions.Timeout):
            logger.error(f"Network timeout: {context} - {error_msg}")
        elif isinstance(error, requests.exceptions.ConnectionError):
            logger.error(f"Connection error: {context} - {error_msg}")
        elif isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, 'status_code', 'unknown')
            logger.error(
                f"HTTP error {status_code}: {context} - {error_msg}"
            )
        else:
            logger.error(f"Network error: {context} - {error_msg}")
        
        return NetworkError(f"{context}: {error_msg}")
    
    @staticmethod
    def handle_graphql_error(error: Exception, query_name: str = "") -> GraphQLError:
        """
        Handle GraphQL API errors with appropriate logging.
        
        Requirement 5.5: GraphQL error handling with appropriate logging
        
        Args:
            error: Original exception
            query_name: Name of the GraphQL query for context
            
        Returns:
            GraphQLError with detailed message
        """
        error_msg = str(error)
        
        logger.error(
            f"GraphQL error in {query_name}: {error_msg}",
            extra={
                'query_name': query_name,
                'error_type': type(error).__name__
            }
        )
        
        return GraphQLError(f"GraphQL query '{query_name}' failed: {error_msg}")
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str = "") -> DatabaseError:
        """
        Handle database errors with appropriate logging and recovery.
        
        Requirement 5.5: Database error handling (duplicate key, foreign key, deadlock)
        
        Args:
            error: Original exception
            operation: Description of the database operation
            
        Returns:
            DatabaseError with detailed message
        """
        error_msg = str(error)
        
        # Handle specific database errors
        if isinstance(error, IntegrityError):
            # Duplicate key or foreign key violation
            if 'Duplicate entry' in error_msg or 'UNIQUE constraint' in error_msg:
                logger.warning(
                    f"Duplicate key in {operation}: {error_msg}. "
                    "This is expected for existing records."
                )
                return DatabaseError(f"Duplicate key: {operation}")
            elif 'foreign key constraint' in error_msg.lower():
                logger.error(
                    f"Foreign key violation in {operation}: {error_msg}"
                )
                return DatabaseError(f"Foreign key violation: {operation}")
            else:
                logger.error(
                    f"Integrity error in {operation}: {error_msg}"
                )
                return DatabaseError(f"Integrity error: {operation}")
        
        elif isinstance(error, OperationalError):
            # Deadlock or connection issues
            if 'deadlock' in error_msg.lower():
                logger.warning(
                    f"Deadlock detected in {operation}: {error_msg}. "
                    "Will retry with backoff."
                )
                return DatabaseError(f"Deadlock: {operation}")
            elif 'lost connection' in error_msg.lower():
                logger.error(
                    f"Database connection lost in {operation}: {error_msg}"
                )
                return DatabaseError(f"Connection lost: {operation}")
            else:
                logger.error(
                    f"Operational error in {operation}: {error_msg}"
                )
                return DatabaseError(f"Operational error: {operation}")
        
        else:
            logger.error(
                f"Database error in {operation}: {error_msg}",
                extra={'error_type': type(error).__name__}
            )
            return DatabaseError(f"Database error: {operation}")
    
    @staticmethod
    def handle_pattern_analysis_error(error: Exception, 
                                      anilist_id: int,
                                      fallback_value: Any = None) -> Any:
        """
        Handle pattern analysis errors with fallback values.
        
        Requirement 5.5: Pattern analysis fallbacks for insufficient data
        
        Args:
            error: Original exception
            anilist_id: Manga ID for context
            fallback_value: Value to return on error
            
        Returns:
            Fallback value
        """
        error_msg = str(error)
        
        logger.warning(
            f"Pattern analysis error for anilist_id {anilist_id}: {error_msg}. "
            f"Using fallback value: {fallback_value}"
        )
        
        return fallback_value


def with_retry(max_attempts: int = 3, 
               initial_delay: float = 1.0,
               max_delay: float = 60.0,
               exponential_base: float = 2.0,
               retry_on: tuple = (NetworkError, OperationalError)):
    """
    Decorator for automatic retry with exponential backoff.
    
    Requirement 5.5: Retry failed jobs with exponential backoff (max 3 attempts)
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        retry_on: Tuple of exception types to retry on
        
    Example:
        @with_retry(max_attempts=3, initial_delay=1.0)
        def scrape_chapters(manga_id):
            # This will retry up to 3 times with exponential backoff
            return api.get_chapters(manga_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Check rate limit before attempting
                    if ErrorHandler.is_rate_limited():
                        rate_info = ErrorHandler.get_rate_limit_info()
                        logger.warning(
                            f"Rate limited, skipping {func.__name__}. "
                            f"Remaining: {rate_info['remaining_seconds']}s"
                        )
                        raise RateLimitError("Currently rate limited")
                    
                    return func(*args, **kwargs)
                    
                except retry_on as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # Calculate delay with exponential backoff
                        delay = min(
                            initial_delay * (exponential_base ** (attempt - 1)),
                            max_delay
                        )
                        
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for "
                            f"{func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for "
                            f"{func.__name__}: {str(e)}"
                        )
                
                except RateLimitError:
                    # Don't retry on rate limit
                    logger.error(f"Rate limited, aborting {func.__name__}")
                    raise
                
                except Exception as e:
                    # Don't retry on unexpected errors
                    logger.error(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        exc_info=True
                    )
                    raise
            
            # All retries exhausted
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def with_database_retry(max_attempts: int = 3):
    """
    Decorator specifically for database operations with deadlock handling.
    
    Requirement 5.5: Database error handling with retry for deadlocks
    
    Args:
        max_attempts: Maximum number of retry attempts
        
    Example:
        @with_database_retry(max_attempts=3)
        def insert_chapters(chapters):
            db_session.bulk_insert_mappings(BatoChapters, chapters)
            db_session.commit()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except OperationalError as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Only retry on deadlock
                    if 'deadlock' in error_msg:
                        if attempt < max_attempts:
                            # Random delay to avoid repeated deadlocks
                            import random
                            delay = random.uniform(0.1, 0.5)
                            
                            logger.warning(
                                f"Deadlock detected in {func.__name__} "
                                f"(attempt {attempt}/{max_attempts}). "
                                f"Retrying in {delay:.2f}s..."
                            )
                            
                            time.sleep(delay)
                        else:
                            logger.error(
                                f"Deadlock persists after {max_attempts} attempts "
                                f"in {func.__name__}"
                            )
                            raise
                    else:
                        # Not a deadlock, don't retry
                        logger.error(
                            f"Database operational error in {func.__name__}: {e}"
                        )
                        raise
                
                except IntegrityError as e:
                    # Don't retry integrity errors (duplicate key, foreign key)
                    error_msg = str(e).lower()
                    
                    if 'duplicate' in error_msg or 'unique constraint' in error_msg:
                        logger.debug(
                            f"Duplicate key in {func.__name__}: {e}. "
                            "Ignoring as expected."
                        )
                        return None  # Return None for duplicate keys
                    else:
                        logger.error(
                            f"Integrity error in {func.__name__}: {e}"
                        )
                        raise
                
                except Exception as e:
                    logger.error(
                        f"Unexpected database error in {func.__name__}: {e}",
                        exc_info=True
                    )
                    raise
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def log_performance(operation_name: str):
    """
    Decorator to log performance metrics for operations.
    
    Requirement 10.5: Track API response times and log when they exceed 2 seconds
    
    Args:
        operation_name: Name of the operation for logging
        
    Example:
        @log_performance("scrape_chapters")
        def scrape_chapters(manga_id):
            return api.get_chapters(manga_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log warning if operation is slow
                if duration > 2.0:
                    logger.warning(
                        f"{operation_name} took {duration:.2f}s (exceeds 2s threshold)",
                        extra={
                            'operation': operation_name,
                            'duration_seconds': duration,
                            'slow_operation': True
                        }
                    )
                else:
                    logger.debug(
                        f"{operation_name} completed in {duration:.2f}s",
                        extra={
                            'operation': operation_name,
                            'duration_seconds': duration
                        }
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation_name} failed after {duration:.2f}s: {str(e)}",
                    extra={
                        'operation': operation_name,
                        'duration_seconds': duration,
                        'error': str(e)
                    }
                )
                raise
        
        return wrapper
    return decorator
