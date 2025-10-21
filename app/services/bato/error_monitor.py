"""
Error Monitor - Track and Report Errors for Bato Notification System

Monitors error rates and provides alerts when thresholds are exceeded.

Requirements:
- 10.4: Log warning when scraping errors exceed 10% over 24 hours
- 10.5: Track API response times and log when they exceed 2 seconds
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class ErrorEvent:
    """Represents a single error event."""
    timestamp: datetime
    error_type: str
    manga_id: Optional[int]
    error_message: str
    duration_seconds: Optional[float] = None


@dataclass
class PerformanceEvent:
    """Represents a performance measurement."""
    timestamp: datetime
    operation: str
    duration_seconds: float
    manga_id: Optional[int] = None


class ErrorMonitor:
    """
    Monitor and track errors and performance metrics.
    
    This class maintains a sliding window of recent errors and performance
    metrics to detect issues and trigger alerts.
    """
    
    # Configuration
    ERROR_RATE_THRESHOLD = 0.10  # 10% error rate triggers warning
    ERROR_RATE_WINDOW_HOURS = 24  # Check error rate over 24 hours
    SLOW_OPERATION_THRESHOLD = 2.0  # Operations over 2s are considered slow
    MAX_EVENTS_STORED = 1000  # Maximum events to keep in memory
    
    def __init__(self):
        """Initialize the error monitor."""
        self._errors: deque = deque(maxlen=self.MAX_EVENTS_STORED)
        self._performance: deque = deque(maxlen=self.MAX_EVENTS_STORED)
        self._total_operations = 0
        self._lock = Lock()
        
        logger.info("ErrorMonitor initialized")
    
    def record_error(self, error_type: str, 
                    error_message: str,
                    manga_id: Optional[int] = None,
                    duration_seconds: Optional[float] = None):
        """
        Record an error event.
        
        Args:
            error_type: Type of error (network, graphql, database, etc.)
            error_message: Error description
            manga_id: Optional manga ID for context
            duration_seconds: Optional duration before error occurred
        """
        with self._lock:
            event = ErrorEvent(
                timestamp=datetime.now(),
                error_type=error_type,
                manga_id=manga_id,
                error_message=error_message,
                duration_seconds=duration_seconds
            )
            
            self._errors.append(event)
            self._total_operations += 1
            
            logger.debug(
                f"Recorded error: {error_type} - {error_message[:100]}"
            )
            
            # Check if we should trigger an alert
            self._check_error_rate()
    
    def record_success(self, operation: str = "scraping"):
        """
        Record a successful operation.
        
        Args:
            operation: Type of operation
        """
        with self._lock:
            self._total_operations += 1
    
    def record_performance(self, operation: str,
                          duration_seconds: float,
                          manga_id: Optional[int] = None):
        """
        Record a performance measurement.
        
        Requirement 10.5: Track API response times
        
        Args:
            operation: Operation name
            duration_seconds: Duration in seconds
            manga_id: Optional manga ID for context
        """
        with self._lock:
            event = PerformanceEvent(
                timestamp=datetime.now(),
                operation=operation,
                duration_seconds=duration_seconds,
                manga_id=manga_id
            )
            
            self._performance.append(event)
            
            # Requirement 10.5: Log when operations exceed 2 seconds
            if duration_seconds > self.SLOW_OPERATION_THRESHOLD:
                logger.warning(
                    f"Slow operation detected: {operation} took {duration_seconds:.2f}s "
                    f"(threshold: {self.SLOW_OPERATION_THRESHOLD}s)",
                    extra={
                        'operation': operation,
                        'duration_seconds': duration_seconds,
                        'manga_id': manga_id,
                        'slow_operation': True
                    }
                )
    
    def _check_error_rate(self):
        """
        Check if error rate exceeds threshold and trigger alert.
        
        Requirement 10.4: Log warning when errors exceed 10% over 24 hours
        """
        cutoff_time = datetime.now() - timedelta(hours=self.ERROR_RATE_WINDOW_HOURS)
        
        # Count recent errors
        recent_errors = sum(
            1 for error in self._errors 
            if error.timestamp >= cutoff_time
        )
        
        # Estimate total operations in window
        # (This is approximate since we don't track all successes)
        if self._total_operations == 0:
            return
        
        # Calculate error rate
        error_rate = recent_errors / min(self._total_operations, len(self._errors) + recent_errors)
        
        # Requirement 10.4: Trigger warning if error rate exceeds 10%
        if error_rate > self.ERROR_RATE_THRESHOLD:
            logger.warning(
                f"HIGH ERROR RATE DETECTED: {error_rate:.1%} over "
                f"{self.ERROR_RATE_WINDOW_HOURS}h "
                f"({recent_errors} errors, threshold: {self.ERROR_RATE_THRESHOLD:.1%})",
                extra={
                    'error_rate': error_rate,
                    'error_count': recent_errors,
                    'window_hours': self.ERROR_RATE_WINDOW_HOURS,
                    'high_error_rate': True
                }
            )
    
    def get_error_summary(self, hours: int = 24) -> Dict:
        """
        Get summary of errors over specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                error for error in self._errors 
                if error.timestamp >= cutoff_time
            ]
            
            if not recent_errors:
                return {
                    'period_hours': hours,
                    'total_errors': 0,
                    'error_rate': 0.0,
                    'errors_by_type': {},
                    'recent_errors': []
                }
            
            # Count by type
            errors_by_type = {}
            for error in recent_errors:
                errors_by_type[error.error_type] = errors_by_type.get(error.error_type, 0) + 1
            
            # Calculate error rate
            total_ops = max(self._total_operations, len(recent_errors))
            error_rate = len(recent_errors) / total_ops
            
            return {
                'period_hours': hours,
                'total_errors': len(recent_errors),
                'error_rate': round(error_rate, 4),
                'error_rate_percentage': round(error_rate * 100, 2),
                'errors_by_type': errors_by_type,
                'recent_errors': [
                    {
                        'timestamp': error.timestamp.isoformat(),
                        'type': error.error_type,
                        'message': error.error_message[:200],
                        'manga_id': error.manga_id
                    }
                    for error in list(recent_errors)[-10:]  # Last 10 errors
                ]
            }
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """
        Get summary of performance metrics over specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with performance statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_performance = [
                perf for perf in self._performance 
                if perf.timestamp >= cutoff_time
            ]
            
            if not recent_performance:
                return {
                    'period_hours': hours,
                    'total_operations': 0,
                    'average_duration': 0.0,
                    'slow_operations': 0,
                    'operations_by_type': {}
                }
            
            # Calculate statistics
            durations = [perf.duration_seconds for perf in recent_performance]
            avg_duration = sum(durations) / len(durations)
            
            slow_operations = sum(
                1 for perf in recent_performance 
                if perf.duration_seconds > self.SLOW_OPERATION_THRESHOLD
            )
            
            # Count by operation type
            operations_by_type = {}
            for perf in recent_performance:
                if perf.operation not in operations_by_type:
                    operations_by_type[perf.operation] = {
                        'count': 0,
                        'total_duration': 0.0,
                        'slow_count': 0
                    }
                
                operations_by_type[perf.operation]['count'] += 1
                operations_by_type[perf.operation]['total_duration'] += perf.duration_seconds
                
                if perf.duration_seconds > self.SLOW_OPERATION_THRESHOLD:
                    operations_by_type[perf.operation]['slow_count'] += 1
            
            # Calculate averages
            for op_type in operations_by_type:
                count = operations_by_type[op_type]['count']
                total = operations_by_type[op_type]['total_duration']
                operations_by_type[op_type]['average_duration'] = round(total / count, 2)
            
            return {
                'period_hours': hours,
                'total_operations': len(recent_performance),
                'average_duration': round(avg_duration, 2),
                'min_duration': round(min(durations), 2),
                'max_duration': round(max(durations), 2),
                'slow_operations': slow_operations,
                'slow_operation_rate': round(slow_operations / len(recent_performance), 4),
                'operations_by_type': operations_by_type
            }
    
    def get_health_status(self) -> Dict:
        """
        Get overall health status of the system.
        
        Returns:
            Dictionary with health indicators
        """
        error_summary = self.get_error_summary(hours=24)
        perf_summary = self.get_performance_summary(hours=24)
        
        # Determine health status
        error_rate = error_summary['error_rate']
        slow_rate = perf_summary.get('slow_operation_rate', 0)
        
        if error_rate > 0.20 or slow_rate > 0.30:
            status = 'critical'
        elif error_rate > 0.10 or slow_rate > 0.20:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'error_rate': error_rate,
            'error_rate_percentage': round(error_rate * 100, 2),
            'slow_operation_rate': slow_rate,
            'slow_operation_rate_percentage': round(slow_rate * 100, 2),
            'total_errors_24h': error_summary['total_errors'],
            'total_operations_24h': perf_summary['total_operations'],
            'average_duration_24h': perf_summary['average_duration'],
            'timestamp': datetime.now().isoformat()
        }
    
    def clear_old_events(self, hours: int = 48):
        """
        Clear events older than specified hours.
        
        Args:
            hours: Age threshold in hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # Filter errors
            self._errors = deque(
                (error for error in self._errors if error.timestamp >= cutoff_time),
                maxlen=self.MAX_EVENTS_STORED
            )
            
            # Filter performance events
            self._performance = deque(
                (perf for perf in self._performance if perf.timestamp >= cutoff_time),
                maxlen=self.MAX_EVENTS_STORED
            )
            
            logger.info(f"Cleared events older than {hours}h")


# Global monitor instance
_monitor_instance: Optional[ErrorMonitor] = None


def get_monitor() -> ErrorMonitor:
    """
    Get or create the global error monitor instance.
    
    Returns:
        ErrorMonitor instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ErrorMonitor()
    return _monitor_instance


def record_error(error_type: str, error_message: str, **kwargs):
    """
    Convenience function to record an error.
    
    Args:
        error_type: Type of error
        error_message: Error description
        **kwargs: Additional context (manga_id, duration_seconds)
    """
    monitor = get_monitor()
    monitor.record_error(error_type, error_message, **kwargs)


def record_success(operation: str = "scraping"):
    """
    Convenience function to record a success.
    
    Args:
        operation: Operation type
    """
    monitor = get_monitor()
    monitor.record_success(operation)


def record_performance(operation: str, duration_seconds: float, **kwargs):
    """
    Convenience function to record performance.
    
    Args:
        operation: Operation name
        duration_seconds: Duration in seconds
        **kwargs: Additional context (manga_id)
    """
    monitor = get_monitor()
    monitor.record_performance(operation, duration_seconds, **kwargs)
