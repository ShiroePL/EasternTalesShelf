"""
Bato.to Notification System Services

This package contains services for the Bato.to notification system:
- ChapterComparator: Detects new chapters by comparing scraped vs database data
- PatternAnalyzer: Analyzes release patterns for intelligent scheduling
- SchedulingEngine: Calculates optimal scraping schedules
- NotificationManager: Creates and manages notifications
- BatoScrapingService: Background service for automated scraping
"""

from .chapter_comparator import ChapterComparator

__all__ = ['ChapterComparator']
