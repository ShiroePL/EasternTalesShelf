"""
SchedulingEngine - Optimal Scraping Schedule Calculator

Calculates when to scrape manga next based on release patterns and history.
Implements adaptive scheduling with min/max intervals and status-based adjustments.

Requirements:
- 3.1: Set initial scraping interval to 24 hours for new manga
- 3.2: Record date_public timestamp when new chapters detected
- 3.3: Calculate average release interval with 3+ releases
- 3.4: Set scraping frequency to 80% of average interval
- 3.5: Enforce minimum scraping interval of 6 hours
- 3.6: Enforce maximum scraping interval of 14 days
- 3.7: Set scraping frequency to 30 days for completed/dropped manga
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
from app.services.bato.pattern_analyzer import PatternAnalyzer
from app.database_module.bato_repository import BatoRepository
import logging
import random

logger = logging.getLogger(__name__)


class SchedulingEngine:
    """
    Service for calculating optimal scraping schedules based on release patterns.
    
    This class implements intelligent scheduling that:
    - Adapts to manga release patterns
    - Enforces min/max interval constraints
    - Adjusts based on scraping results
    - Handles status changes (completed/dropped)
    """
    
    # Constants for scheduling (from requirements)
    DEFAULT_INTERVAL_HOURS = 24  # Requirement 3.1
    MIN_INTERVAL_HOURS = 6  # Requirement 3.5
    MAX_INTERVAL_DAYS = 14  # Requirement 3.6
    COMPLETED_DROPPED_INTERVAL_DAYS = 30  # Requirement 3.7
    
    INTERVAL_MULTIPLIER = 0.80  # Requirement 3.4: 80% of average
    MIN_RELEASES_FOR_PATTERN = 3  # Requirement 3.3
    
    # Adjustment factors for inactive manga
    NO_UPDATE_PENALTY_MULTIPLIER = 1.5  # Increase interval by 50% when no updates
    MAX_NO_UPDATE_INCREASES = 3  # Stop increasing after 3 consecutive no-updates
    
    # Time-based thresholds for inactive manga handling
    DAYS_INACTIVE_SHORT = 30  # Less than 30 days = recently active
    DAYS_INACTIVE_MEDIUM = 90  # 30-90 days = moderately inactive
    DAYS_INACTIVE_LONG = 180  # 90-180 days = very inactive
    # Over 180 days = likely abandoned, but keep checking occasionally
    
    # Max interval even with penalties (prevents extreme scheduling)
    ABSOLUTE_MAX_INTERVAL_DAYS = 21  # Never schedule more than 3 weeks out
    
    # Jitter/randomization for schedule spreading (STEALTH FEATURE)
    # Adds random time to schedules to prevent predictable patterns
    # This spreads scraping across hours/days instead of clustering
    JITTER_MIN_HOURS = -2  # Can schedule up to 2 hours earlier
    JITTER_MAX_HOURS = 6   # Can schedule up to 6 hours later
    # Result: Same manga scraped at different times each cycle
    
    def __init__(self):
        """Initialize the SchedulingEngine with dependencies."""
        self.pattern_analyzer = PatternAnalyzer()
        self.repository = BatoRepository()
    
    def _get_days_since_last_chapter(self, anilist_id: int) -> Optional[float]:
        """
        Calculate how many days since the last chapter was released.
        
        This helps determine if manga is still actively releasing or has gone inactive.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            Days since last chapter release, or None if no chapters found
        """
        try:
            chapter_dates = self.repository.get_chapter_dates(anilist_id, limit=1)
            
            if not chapter_dates:
                return None
            
            last_chapter_date = chapter_dates[0]
            days_since = (datetime.now() - last_chapter_date).total_seconds() / 86400
            
            return days_since
            
        except Exception as e:
            logger.error(f"Error calculating days since last chapter for anilist_id {anilist_id}: {e}")
            return None
    
    def _apply_schedule_jitter(self, next_scrape_time: datetime, anilist_id: int) -> datetime:
        """
        Apply random jitter to schedule time for stealth and pattern breaking.
        
        This is a CRITICAL stealth feature that prevents predictable scraping patterns.
        Without jitter, all manga get scraped at the same relative times, creating
        obvious automated patterns. With jitter, scraping times drift and spread out,
        looking like organic human browsing.
        
        Benefits:
        - Prevents clustering (50 manga all scraped at 3pm every day)
        - Makes detection nearly impossible (no predictable patterns)
        - Spreads server load naturally over time
        - Each manga drifts to different times over multiple cycles
        
        Example:
        Without jitter: Manga scraped at 15:00, 15:02, 15:05 every day
        With jitter: First cycle 15:00, 14:23, 16:45, next cycle 16:12, 13:58, 17:22
        
        Args:
            next_scrape_time: Calculated next scrape time
            anilist_id: Manga ID (used for logging)
            
        Returns:
            Adjusted scrape time with random jitter applied
        """
        try:
            # Generate random jitter in hours
            jitter_hours = random.uniform(self.JITTER_MIN_HOURS, self.JITTER_MAX_HOURS)
            
            # Apply jitter
            jittered_time = next_scrape_time + timedelta(hours=jitter_hours)
            
            # Ensure we don't schedule in the past
            now = datetime.now()
            if jittered_time < now:
                # If jitter pushed it to the past, just use a small random delay from now
                jittered_time = now + timedelta(minutes=random.randint(5, 30))
                logger.debug(
                    f"Jitter resulted in past time for anilist_id {anilist_id}, "
                    f"rescheduling to {jittered_time.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                logger.debug(
                    f"Applied jitter for anilist_id {anilist_id}: "
                    f"{jitter_hours:+.2f}h (original: {next_scrape_time.strftime('%H:%M')}, "
                    f"jittered: {jittered_time.strftime('%H:%M')})"
                )
            
            return jittered_time
            
        except Exception as e:
            logger.error(f"Error applying jitter for anilist_id {anilist_id}: {e}")
            # Return original time if jitter fails
            return next_scrape_time
    
    def calculate_next_scrape_time(self, anilist_id: int, 
                                   current_time: Optional[datetime] = None) -> datetime:
        """
        Calculate when to scrape next based on pattern analysis.
        
        This is the main method that orchestrates all scheduling logic:
        1. Check upload_status for completed/dropped (30 days)
        2. Analyze release patterns
        3. Calculate interval (80% of average or weekly pattern)
        4. Apply min/max constraints
        5. Adjust for consecutive no-updates
        
        Args:
            anilist_id: AniList manga ID
            current_time: Reference time (defaults to now)
            
        Returns:
            datetime when next scrape should occur
            
        Requirements:
            - 3.1: Default 24h for new manga
            - 3.3-3.4: Pattern-based scheduling
            - 3.5-3.6: Min/max enforcement
            - 3.7: Status-based adjustments
        """
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Get manga details and schedule
            manga_details = self.repository.get_manga_details(anilist_id)
            schedule = self.repository.get_schedule(anilist_id)
            
            if not manga_details:
                logger.warning(f"No manga details found for anilist_id {anilist_id}")
                return current_time + timedelta(hours=self.DEFAULT_INTERVAL_HOURS)
            
            # Requirement 3.7: Check upload_status for completed/dropped
            if manga_details.upload_status in ['completed', 'dropped']:
                logger.info(
                    f"Manga {anilist_id} is {manga_details.upload_status}, "
                    f"setting interval to {self.COMPLETED_DROPPED_INTERVAL_DAYS} days"
                )
                return current_time + timedelta(days=self.COMPLETED_DROPPED_INTERVAL_DAYS)
            
            # Get chapter dates for pattern analysis
            chapter_dates = self.repository.get_chapter_dates(anilist_id)
            
            # Check how long since last chapter was released
            days_since_last_chapter = self._get_days_since_last_chapter(anilist_id)
            
            # If insufficient data, use default interval (Requirement 3.1)
            if not chapter_dates or len(chapter_dates) < self.MIN_RELEASES_FOR_PATTERN:
                logger.info(
                    f"Insufficient data for anilist_id {anilist_id} "
                    f"({len(chapter_dates) if chapter_dates else 0} releases), "
                    f"using default {self.DEFAULT_INTERVAL_HOURS}h interval"
                )
                return current_time + timedelta(hours=self.DEFAULT_INTERVAL_HOURS)
            
            # Calculate interval based on patterns
            interval_hours = self._calculate_interval_from_pattern(chapter_dates, schedule)
            
            # Adjust interval based on inactivity (smarter scheduling for abandoned manga)
            if days_since_last_chapter is not None:
                interval_hours = self._adjust_for_inactivity(
                    interval_hours, 
                    days_since_last_chapter,
                    anilist_id
                )
            
            # Apply min/max constraints (Requirements 3.5, 3.6)
            interval_hours = self._enforce_interval_constraints(interval_hours)
            
            # Apply absolute maximum to prevent extreme scheduling
            absolute_max_hours = self.ABSOLUTE_MAX_INTERVAL_DAYS * 24
            if interval_hours > absolute_max_hours:
                logger.warning(
                    f"Interval {interval_hours:.1f}h exceeds absolute maximum, "
                    f"capping at {absolute_max_hours}h ({self.ABSOLUTE_MAX_INTERVAL_DAYS} days) "
                    f"for anilist_id {anilist_id}"
                )
                interval_hours = float(absolute_max_hours)
            
            # Calculate next scrape time
            next_scrape_time = current_time + timedelta(hours=interval_hours)
            
            # Apply random jitter to prevent predictable patterns (STEALTH FEATURE)
            next_scrape_time = self._apply_schedule_jitter(next_scrape_time, anilist_id)
            
            # Enhanced logging with context
            log_parts = [
                f"anilist_id {anilist_id}:",
                f"next_scrape={next_scrape_time.strftime('%Y-%m-%d %H:%M')}",
                f"interval={interval_hours:.1f}h ({interval_hours/24:.1f} days)"
            ]
            
            if days_since_last_chapter is not None:
                log_parts.append(f"days_since_last_chapter={days_since_last_chapter:.1f}")
            
            if schedule and schedule.consecutive_no_update_count > 0:
                log_parts.append(f"no_updates={schedule.consecutive_no_update_count}")
            
            logger.info("Calculated next scrape (with jitter): " + ", ".join(log_parts))
            
            return next_scrape_time
            
        except Exception as e:
            logger.error(f"Error calculating next scrape time for anilist_id {anilist_id}: {e}")
            # Fallback to default interval
            return current_time + timedelta(hours=self.DEFAULT_INTERVAL_HOURS)
    
    def _calculate_interval_from_pattern(self, chapter_dates: list, 
                                        schedule: Optional[object]) -> float:
        """
        Calculate scraping interval based on release patterns.
        
        Uses PatternAnalyzer to detect patterns and applies the 80% multiplier
        as specified in Requirement 3.4.
        
        Args:
            chapter_dates: List of chapter publication dates
            schedule: Current schedule object (for no-update adjustments)
            
        Returns:
            Interval in hours
        """
        try:
            # Try weekly pattern first
            preferred_day = self.pattern_analyzer.detect_weekly_pattern(chapter_dates)
            
            if preferred_day is not None:
                # Weekly pattern detected: scrape on preferred day + 1 day buffer
                # This means checking once per week (168 hours)
                interval_hours = 168.0  # 7 days
                logger.debug(
                    f"Using weekly pattern interval: {interval_hours}h "
                    f"(preferred day: {preferred_day})"
                )
                return interval_hours
            
            # Fall back to average interval (Requirement 3.3, 3.4)
            avg_interval_days = self.pattern_analyzer.calculate_average_interval(chapter_dates)
            
            if avg_interval_days:
                # Apply 80% multiplier (Requirement 3.4)
                interval_days = avg_interval_days * self.INTERVAL_MULTIPLIER
                interval_hours = interval_days * 24
                
                logger.info(
                    f"Using average interval: {avg_interval_days:.1f} days "
                    f"* {self.INTERVAL_MULTIPLIER} = {interval_hours:.1f}h "
                    f"({interval_days:.1f} days)"
                )
                
                # Apply no-update penalty if applicable
                if schedule and schedule.consecutive_no_update_count > 0:
                    interval_hours = self._apply_no_update_penalty(
                        interval_hours, 
                        schedule.consecutive_no_update_count
                    )
                
                return interval_hours
            
            # No pattern detected, use default
            logger.debug("No pattern detected, using default interval")
            return float(self.DEFAULT_INTERVAL_HOURS)
            
        except Exception as e:
            logger.error(f"Error calculating interval from pattern: {e}")
            return float(self.DEFAULT_INTERVAL_HOURS)
    
    def _enforce_interval_constraints(self, interval_hours: float) -> float:
        """
        Enforce minimum and maximum interval constraints.
        
        Requirements:
        - 3.5: Minimum 6 hours
        - 3.6: Maximum 14 days
        
        Args:
            interval_hours: Calculated interval in hours
            
        Returns:
            Constrained interval in hours
        """
        original_interval = interval_hours
        
        # Requirement 3.5: Minimum 6 hours
        if interval_hours < self.MIN_INTERVAL_HOURS:
            interval_hours = float(self.MIN_INTERVAL_HOURS)
            logger.debug(
                f"Interval {original_interval:.1f}h below minimum, "
                f"enforcing {self.MIN_INTERVAL_HOURS}h"
            )
        
        # Requirement 3.6: Maximum 14 days (336 hours)
        max_interval_hours = self.MAX_INTERVAL_DAYS * 24
        if interval_hours > max_interval_hours:
            interval_hours = float(max_interval_hours)
            logger.debug(
                f"Interval {original_interval:.1f}h above maximum, "
                f"enforcing {max_interval_hours}h ({self.MAX_INTERVAL_DAYS} days)"
            )
        
        return interval_hours
    
    def _adjust_for_inactivity(self, interval_hours: float, 
                               days_since_last_chapter: float,
                               anilist_id: int) -> float:
        """
        Adjust interval based on how long since last chapter was released.
        
        Strategy:
        - Recently active (<30 days): Keep checking frequently, no penalty
        - Moderately inactive (30-90 days): Slight increase, check weekly
        - Very inactive (90-180 days): Check every 2 weeks
        - Likely abandoned (>180 days): Check every 3 weeks, but don't give up
        
        This prevents the system from over-checking manga that haven't updated in months
        while ensuring we don't completely abandon them.
        
        Args:
            interval_hours: Base interval in hours
            days_since_last_chapter: Days since last chapter release
            anilist_id: Manga ID for logging
            
        Returns:
            Adjusted interval in hours
        """
        if days_since_last_chapter <= self.DAYS_INACTIVE_SHORT:
            # Recently active - no adjustment needed
            logger.debug(
                f"Manga {anilist_id} is recently active ({days_since_last_chapter:.1f} days), "
                f"no inactivity adjustment"
            )
            return interval_hours
        
        elif days_since_last_chapter <= self.DAYS_INACTIVE_MEDIUM:
            # Moderately inactive - check weekly
            target_hours = 168.0  # 7 days
            adjusted = max(interval_hours, target_hours)
            logger.info(
                f"Manga {anilist_id} moderately inactive ({days_since_last_chapter:.1f} days), "
                f"adjusted interval to {adjusted:.1f}h (weekly checks)"
            )
            return adjusted
        
        elif days_since_last_chapter <= self.DAYS_INACTIVE_LONG:
            # Very inactive - check every 2 weeks
            target_hours = 336.0  # 14 days
            adjusted = max(interval_hours, target_hours)
            logger.info(
                f"Manga {anilist_id} very inactive ({days_since_last_chapter:.1f} days), "
                f"adjusted interval to {adjusted:.1f}h (bi-weekly checks)"
            )
            return adjusted
        
        else:
            # Likely abandoned - check every 3 weeks, but don't give up entirely
            target_hours = 504.0  # 21 days
            logger.warning(
                f"Manga {anilist_id} likely abandoned ({days_since_last_chapter:.1f} days since last chapter), "
                f"setting interval to {target_hours:.1f}h (3-week checks)"
            )
            return target_hours
    
    def _apply_no_update_penalty(self, interval_hours: float, 
                                consecutive_no_updates: int) -> float:
        """
        Increase interval when no updates found repeatedly.
        
        This helps reduce unnecessary scraping for manga that haven't
        updated in a while. Increases by 50% per consecutive no-update,
        up to a maximum of 3 increases.
        
        NOTE: This penalty is now LESS aggressive because the inactivity
        adjustment already handles long-dormant manga. This penalty is for
        manga that were recently active but haven't had updates in the
        last few scrapes.
        
        Args:
            interval_hours: Base interval in hours
            consecutive_no_updates: Number of consecutive scrapes with no updates
            
        Returns:
            Adjusted interval in hours
        """
        if consecutive_no_updates <= 0:
            return interval_hours
        
        # Only apply penalty for short-to-medium intervals
        # If interval is already long (>7 days), don't penalize further
        if interval_hours > 168:  # More than 7 days
            logger.debug(
                f"Interval already long ({interval_hours:.1f}h), "
                f"skipping no-update penalty"
            )
            return interval_hours
        
        # Cap at MAX_NO_UPDATE_INCREASES
        effective_count = min(consecutive_no_updates, self.MAX_NO_UPDATE_INCREASES)
        
        # Apply multiplier for each consecutive no-update
        multiplier = self.NO_UPDATE_PENALTY_MULTIPLIER ** effective_count
        adjusted_interval = interval_hours * multiplier
        
        logger.debug(
            f"Applied no-update penalty: {interval_hours:.1f}h * "
            f"{multiplier:.2f} = {adjusted_interval:.1f}h "
            f"({effective_count} consecutive no-updates)"
        )
        
        return adjusted_interval
    
    def update_schedule_after_scrape(self, anilist_id: int, 
                                    new_chapters_found: int,
                                    current_time: Optional[datetime] = None) -> bool:
        """
        Update schedule based on scraping results.
        
        This method:
        1. Calculates next scrape time using pattern analysis
        2. Updates schedule in database
        3. Resets or increments consecutive_no_update_count
        4. Updates pattern analysis data if new chapters found
        
        Args:
            anilist_id: AniList manga ID
            new_chapters_found: Number of new chapters detected
            current_time: Reference time (defaults to now)
            
        Returns:
            True if successful, False otherwise
        """
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Calculate next scrape time
            next_scrape_at = self.calculate_next_scrape_time(anilist_id, current_time)
            
            # Update schedule in database
            success = self.repository.update_schedule_after_scrape(
                anilist_id=anilist_id,
                next_scrape_at=next_scrape_at,
                new_chapters_found=new_chapters_found
            )
            
            if success:
                # Update pattern analysis if new chapters found
                if new_chapters_found > 0:
                    self._update_pattern_analysis(anilist_id)
                
                logger.info(
                    f"Updated schedule for anilist_id {anilist_id}: "
                    f"next scrape at {next_scrape_at.strftime('%Y-%m-%d %H:%M')}, "
                    f"{new_chapters_found} new chapters found"
                )
                return True
            else:
                logger.error(f"Failed to update schedule for anilist_id {anilist_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating schedule after scrape for anilist_id {anilist_id}: {e}")
            return False
    
    def _update_pattern_analysis(self, anilist_id: int):
        """
        Update pattern analysis data in schedule.
        
        Recalculates average interval, preferred day, and confidence score
        based on current chapter data.
        
        Args:
            anilist_id: AniList manga ID
        """
        try:
            # Get current chapter dates
            chapter_dates = self.repository.get_chapter_dates(anilist_id)
            
            if not chapter_dates or len(chapter_dates) < self.MIN_RELEASES_FOR_PATTERN:
                return
            
            # Calculate pattern metrics
            avg_interval = self.pattern_analyzer.calculate_average_interval(chapter_dates)
            preferred_day = self.pattern_analyzer.detect_weekly_pattern(chapter_dates)
            confidence = self.pattern_analyzer.calculate_confidence_score(chapter_dates)
            
            # Get current schedule
            schedule = self.repository.get_schedule(anilist_id)
            if not schedule:
                return
            
            # Calculate interval in hours for storage
            if avg_interval:
                interval_hours = int(avg_interval * 24 * self.INTERVAL_MULTIPLIER)
                interval_hours = max(self.MIN_INTERVAL_HOURS, 
                                   min(interval_hours, self.MAX_INTERVAL_DAYS * 24))
            else:
                interval_hours = self.DEFAULT_INTERVAL_HOURS
            
            # Update schedule with pattern data
            schedule_data = {
                'anilist_id': anilist_id,
                'bato_link': schedule.bato_link,
                'average_release_interval_days': avg_interval,
                'preferred_release_day': preferred_day,
                'release_pattern_confidence': confidence,
                'scraping_interval_hours': interval_hours,
                'last_chapter_date': chapter_dates[0] if chapter_dates else None
            }
            
            self.repository.upsert_schedule(schedule_data)
            
            logger.debug(
                f"Updated pattern analysis for anilist_id {anilist_id}: "
                f"avg_interval={avg_interval:.1f}d, "
                f"preferred_day={preferred_day}, "
                f"confidence={confidence:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error updating pattern analysis for anilist_id {anilist_id}: {e}")
    
    def adjust_for_no_updates(self, anilist_id: int) -> bool:
        """
        Increase interval when no new chapters found.
        
        This method is called when a scrape finds no new chapters.
        It increments the consecutive_no_update_count and recalculates
        the next scrape time with the penalty applied.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            schedule = self.repository.get_schedule(anilist_id)
            
            if not schedule:
                logger.warning(f"No schedule found for anilist_id {anilist_id}")
                return False
            
            # Increment no-update count (capped at MAX_NO_UPDATE_INCREASES)
            new_count = min(
                schedule.consecutive_no_update_count + 1,
                self.MAX_NO_UPDATE_INCREASES
            )
            
            # Calculate new interval with penalty
            current_time = datetime.now()
            next_scrape_at = self.calculate_next_scrape_time(anilist_id, current_time)
            
            # Update schedule
            schedule_data = {
                'anilist_id': anilist_id,
                'bato_link': schedule.bato_link,
                'next_scrape_at': next_scrape_at,
                'last_scraped_at': current_time,
                'consecutive_no_update_count': new_count
            }
            
            result = self.repository.upsert_schedule(schedule_data)
            
            if result:
                logger.info(
                    f"Adjusted schedule for no updates (anilist_id {anilist_id}): "
                    f"consecutive_no_update_count={new_count}, "
                    f"next_scrape_at={next_scrape_at.strftime('%Y-%m-%d %H:%M')}"
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error adjusting for no updates (anilist_id {anilist_id}): {e}")
            return False
    
    def create_initial_schedule(self, anilist_id: int, bato_link: str,
                               current_time: Optional[datetime] = None) -> bool:
        """
        Create initial schedule for a new manga.
        
        Sets default 24-hour interval as per Requirement 3.1.
        
        Args:
            anilist_id: AniList manga ID
            bato_link: Bato.to manga URL
            current_time: Reference time (defaults to now)
            
        Returns:
            True if successful, False otherwise
        """
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Requirement 3.1: Initial interval is 24 hours
            next_scrape_at = current_time + timedelta(hours=self.DEFAULT_INTERVAL_HOURS)
            
            schedule_data = {
                'anilist_id': anilist_id,
                'bato_link': bato_link,
                'scraping_interval_hours': self.DEFAULT_INTERVAL_HOURS,
                'next_scrape_at': next_scrape_at,
                'is_active': True,
                'priority': 1
            }
            
            result = self.repository.upsert_schedule(schedule_data)
            
            if result:
                logger.info(
                    f"Created initial schedule for anilist_id {anilist_id}: "
                    f"interval={self.DEFAULT_INTERVAL_HOURS}h, "
                    f"next_scrape_at={next_scrape_at.strftime('%Y-%m-%d %H:%M')}"
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error creating initial schedule for anilist_id {anilist_id}: {e}")
            return False
    
    def get_schedule_info(self, anilist_id: int) -> Optional[Dict]:
        """
        Get comprehensive schedule information for a manga.
        
        This is a convenience method that returns all scheduling data
        including pattern analysis and next scrape time.
        
        Args:
            anilist_id: AniList manga ID
            
        Returns:
            Dictionary with schedule information or None
        """
        try:
            schedule = self.repository.get_schedule(anilist_id)
            
            if not schedule:
                return None
            
            # Get pattern summary
            chapter_dates = self.repository.get_chapter_dates(anilist_id)
            pattern_summary = self.pattern_analyzer.get_pattern_summary(chapter_dates)
            
            return {
                'anilist_id': schedule.anilist_id,
                'scraping_interval_hours': schedule.scraping_interval_hours,
                'last_scraped_at': schedule.last_scraped_at,
                'next_scrape_at': schedule.next_scrape_at,
                'average_release_interval_days': schedule.average_release_interval_days,
                'preferred_release_day': schedule.preferred_release_day,
                'release_pattern_confidence': schedule.release_pattern_confidence,
                'total_chapters_tracked': schedule.total_chapters_tracked,
                'last_chapter_date': schedule.last_chapter_date,
                'consecutive_no_update_count': schedule.consecutive_no_update_count,
                'is_active': schedule.is_active,
                'priority': schedule.priority,
                'pattern_analysis': pattern_summary
            }
            
        except Exception as e:
            logger.error(f"Error getting schedule info for anilist_id {anilist_id}: {e}")
            return None
