"""
Logging Configuration for Bato Notification System

Provides comprehensive logging setup for debugging and monitoring.

Requirements:
- 10.1, 10.2, 10.5: Comprehensive logging for debugging and monitoring
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_bato_logging(log_level: str = 'INFO', 
                       log_to_file: bool = True,
                       log_dir: str = 'logs/bato') -> logging.Logger:
    """
    Setup comprehensive logging for Bato notification system.
    
    Creates separate log files for:
    - General operations (bato.log)
    - Errors only (bato_errors.log)
    - Performance metrics (bato_performance.log)
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to files
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('bato')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (always enabled)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handlers (if enabled)
    if log_to_file:
        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # General log file (rotating)
        general_log = log_path / 'bato.log'
        general_handler = logging.handlers.RotatingFileHandler(
            general_log,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        general_handler.setLevel(logging.DEBUG)
        general_handler.setFormatter(detailed_formatter)
        logger.addHandler(general_handler)
        
        # Error log file (errors only)
        error_log = log_path / 'bato_errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
        
        # Performance log file (for slow operations)
        performance_log = log_path / 'bato_performance.log'
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3
        )
        performance_handler.setLevel(logging.WARNING)
        performance_handler.addFilter(PerformanceFilter())
        performance_handler.setFormatter(detailed_formatter)
        logger.addHandler(performance_handler)
    
    logger.info(f"Bato logging initialized (level: {log_level})")
    
    return logger


class PerformanceFilter(logging.Filter):
    """
    Filter to capture only performance-related log messages.
    
    Captures messages with:
    - 'slow_operation' in extra data
    - Duration information
    - Performance warnings
    """
    
    def filter(self, record):
        """
        Determine if record should be logged.
        
        Args:
            record: LogRecord to filter
            
        Returns:
            True if record should be logged, False otherwise
        """
        # Check for performance-related attributes
        if hasattr(record, 'slow_operation') and record.slow_operation:
            return True
        
        if hasattr(record, 'duration_seconds'):
            return True
        
        # Check message content
        message = record.getMessage().lower()
        performance_keywords = [
            'took',
            'duration',
            'slow',
            'timeout',
            'exceeds',
            'performance'
        ]
        
        return any(keyword in message for keyword in performance_keywords)


def get_bato_logger(name: str = 'bato') -> logging.Logger:
    """
    Get a logger instance for Bato system.
    
    Args:
        name: Logger name (will be prefixed with 'bato.')
        
    Returns:
        Logger instance
    """
    if not name.startswith('bato'):
        name = f'bato.{name}'
    
    return logging.getLogger(name)


def log_scraping_metrics(manga_name: str,
                         duration: float,
                         chapters_found: int,
                         new_chapters: int,
                         success: bool):
    """
    Log scraping metrics in a structured format.
    
    Requirement 10.1, 10.2: Record duration_seconds, chapters_found, new_chapters
    
    Args:
        manga_name: Name of the manga
        duration: Scraping duration in seconds
        chapters_found: Total chapters scraped
        new_chapters: Number of new chapters detected
        success: Whether scraping was successful
    """
    logger = get_bato_logger('metrics')
    
    status = 'SUCCESS' if success else 'FAILED'
    
    logger.info(
        f"SCRAPE_METRICS | {status} | {manga_name} | "
        f"duration={duration:.2f}s | "
        f"chapters_found={chapters_found} | "
        f"new_chapters={new_chapters}",
        extra={
            'manga_name': manga_name,
            'duration_seconds': duration,
            'chapters_found': chapters_found,
            'new_chapters': new_chapters,
            'success': success
        }
    )


def log_error_rate(period_hours: int, error_count: int, total_count: int):
    """
    Log error rate for monitoring.
    
    Requirement 10.4: Log warning when scraping errors exceed 10% over 24 hours
    
    Args:
        period_hours: Time period in hours
        error_count: Number of errors
        total_count: Total number of operations
    """
    logger = get_bato_logger('monitoring')
    
    if total_count == 0:
        return
    
    error_rate = (error_count / total_count) * 100
    
    if error_rate > 10.0:
        logger.warning(
            f"HIGH_ERROR_RATE | {error_rate:.1f}% errors over {period_hours}h "
            f"({error_count}/{total_count} jobs failed)",
            extra={
                'error_rate': error_rate,
                'error_count': error_count,
                'total_count': total_count,
                'period_hours': period_hours,
                'high_error_rate': True
            }
        )
    else:
        logger.info(
            f"Error rate: {error_rate:.1f}% over {period_hours}h "
            f"({error_count}/{total_count} jobs)",
            extra={
                'error_rate': error_rate,
                'error_count': error_count,
                'total_count': total_count,
                'period_hours': period_hours
            }
        )


def log_rate_limit_event(retry_after: int, count: int):
    """
    Log rate limiting events.
    
    Requirement 5.5: Rate limiting detection with 5-minute pause
    
    Args:
        retry_after: Seconds until rate limit expires
        count: Number of times rate limited
    """
    logger = get_bato_logger('rate_limit')
    
    logger.warning(
        f"RATE_LIMITED | Pausing for {retry_after}s | "
        f"Rate limit count: {count}",
        extra={
            'retry_after_seconds': retry_after,
            'rate_limit_count': count,
            'rate_limited': True
        }
    )


# Initialize logging on module import
_default_logger = None


def init_logging(log_level: str = 'INFO', log_to_file: bool = True):
    """
    Initialize Bato logging system.
    
    Should be called once at application startup.
    
    Args:
        log_level: Logging level
        log_to_file: Whether to enable file logging
    """
    global _default_logger
    _default_logger = setup_bato_logging(log_level, log_to_file)
    return _default_logger
