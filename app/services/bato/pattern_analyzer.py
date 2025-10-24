"""
PatternAnalyzer - Release Pattern Detection Service

Analyzes chapter release history to detect patterns and predict future releases.
Implements statistical analysis for weekly patterns and average intervals.

Requirements:
- 4.1: Analyze day-of-week distribution with 5+ releases
- 4.2: Detect preferred release day (60% threshold)
- 4.3: Schedule scraping for preferred day plus one day buffer
- 4.4: Use interval-based scheduling when no clear pattern exists
- 4.5: Recalculate patterns over 10 releases when changes detected
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """
    Service for analyzing manga release patterns to optimize scraping schedules.
    
    This class implements statistical analysis of chapter release dates to:
    - Calculate average intervals between releases
    - Detect weekly release patterns
    - Calculate confidence scores for detected patterns
    - Predict next release dates
    """
    
    # Constants for pattern detection
    MIN_RELEASES_FOR_PATTERN = 5  # Minimum releases needed for pattern analysis
    WEEKLY_PATTERN_THRESHOLD = 0.60  # 60% of releases on same day
    MIN_RELEASES_FOR_CONFIDENCE = 3  # Minimum for confidence calculation
    
    def __init__(self):
        """Initialize the PatternAnalyzer."""
        pass
    
    def calculate_average_interval(self, chapter_dates: List[datetime]) -> Optional[float]:
        """
        Calculate average days between releases with error handling.
        
        This method computes the mean interval between consecutive chapter releases,
        which is used as a baseline for scheduling when no weekly pattern is detected.
        
        Implements fallback for insufficient data as per Requirement 5.5.
        
        Args:
            chapter_dates: List of datetime objects (should be sorted, newest first)
            
        Returns:
            Average interval in days (float) or None if insufficient data
            
        Example:
            >>> analyzer = PatternAnalyzer()
            >>> dates = [
            ...     datetime(2024, 1, 15),
            ...     datetime(2024, 1, 8),
            ...     datetime(2024, 1, 1)
            ... ]
            >>> analyzer.calculate_average_interval(dates)
            7.0
        """
        # Requirement 5.5: Pattern analysis fallbacks for insufficient data
        if not chapter_dates or len(chapter_dates) < 2:
            logger.debug(
                f"Insufficient data for average interval calculation "
                f"(need 2+, have {len(chapter_dates) if chapter_dates else 0}). "
                "Returning None as fallback."
            )
            return None
        
        try:
            # Sort dates in descending order (newest first) if not already sorted
            sorted_dates = sorted(chapter_dates, reverse=True)
            
            # Calculate intervals between consecutive releases
            intervals = []
            for i in range(len(sorted_dates) - 1):
                newer_date = sorted_dates[i]
                older_date = sorted_dates[i + 1]
                
                # Validate dates
                if not isinstance(newer_date, datetime) or not isinstance(older_date, datetime):
                    logger.warning(
                        f"Invalid date type at index {i}: "
                        f"{type(newer_date)}, {type(older_date)}. Skipping."
                    )
                    continue
                
                interval_days = (newer_date - older_date).total_seconds() / 86400
                
                # Sanity check: ignore negative or extremely large intervals
                if interval_days < 0:
                    logger.warning(
                        f"Negative interval detected: {interval_days:.2f} days. "
                        "Dates may be out of order. Skipping."
                    )
                    continue
                elif interval_days > 365:
                    logger.warning(
                        f"Extremely large interval detected: {interval_days:.2f} days. "
                        "Skipping as outlier."
                    )
                    continue
                
                intervals.append(interval_days)
            
            if not intervals:
                logger.warning(
                    "No valid intervals calculated. Returning None as fallback."
                )
                return None
            
            # Calculate average
            average_interval = sum(intervals) / len(intervals)
            
            logger.info(
                f"Calculated average interval: {average_interval:.2f} days "
                f"from {len(intervals)} intervals"
            )
            
            return average_interval
            
        except Exception as e:
            # Requirement 5.5: Pattern analysis fallbacks
            logger.error(
                f"Error calculating average interval: {e}. "
                "Returning None as fallback.",
                exc_info=True
            )
            return None
    
    def get_day_of_week_distribution(self, chapter_dates: List[datetime]) -> Dict[int, int]:
        """
        Calculate which days chapters are typically released.
        
        Returns a distribution of releases by day of week (0=Monday, 6=Sunday).
        This is a helper method used by detect_weekly_pattern().
        
        Args:
            chapter_dates: List of datetime objects
            
        Returns:
            Dictionary mapping day_of_week (0-6) to count of releases
            
        Example:
            >>> analyzer = PatternAnalyzer()
            >>> dates = [
            ...     datetime(2024, 1, 15),  # Monday
            ...     datetime(2024, 1, 8),   # Monday
            ...     datetime(2024, 1, 1)    # Monday
            ... ]
            >>> analyzer.get_day_of_week_distribution(dates)
            {0: 3}
        """
        if not chapter_dates:
            return {}
        
        try:
            # Get day of week for each date (0=Monday, 6=Sunday)
            days_of_week = [date.weekday() for date in chapter_dates]
            
            # Count occurrences of each day
            distribution = Counter(days_of_week)
            
            logger.debug(f"Day of week distribution: {dict(distribution)}")
            
            return dict(distribution)
            
        except Exception as e:
            logger.error(f"Error calculating day of week distribution: {e}")
            return {}
    
    def detect_weekly_pattern(self, chapter_dates: List[datetime]) -> Optional[int]:
        """
        Detect if releases follow a weekly pattern.
        
        According to requirement 4.2, when a specific day has 60% or more of releases,
        that day should be marked as the preferred_release_day.
        
        Args:
            chapter_dates: List of datetime objects
            
        Returns:
            Day of week (0=Monday, 6=Sunday) if pattern detected, None otherwise
            
        Example:
            >>> analyzer = PatternAnalyzer()
            >>> # 4 out of 5 releases on Monday (80% > 60% threshold)
            >>> dates = [
            ...     datetime(2024, 1, 15),  # Monday
            ...     datetime(2024, 1, 8),   # Monday
            ...     datetime(2024, 1, 3),   # Wednesday
            ...     datetime(2023, 12, 25), # Monday
            ...     datetime(2023, 12, 18)  # Monday
            ... ]
            >>> analyzer.detect_weekly_pattern(dates)
            0  # Monday
        """
        if not chapter_dates or len(chapter_dates) < self.MIN_RELEASES_FOR_PATTERN:
            logger.debug(
                f"Insufficient data for weekly pattern detection "
                f"(need {self.MIN_RELEASES_FOR_PATTERN}, have {len(chapter_dates)})"
            )
            return None
        
        try:
            # Get day of week distribution
            distribution = self.get_day_of_week_distribution(chapter_dates)
            
            if not distribution:
                return None
            
            # Find the most common day
            total_releases = len(chapter_dates)
            most_common_day = max(distribution, key=distribution.get)
            most_common_count = distribution[most_common_day]
            
            # Calculate percentage
            percentage = most_common_count / total_releases
            
            # Check if it meets the threshold
            if percentage >= self.WEEKLY_PATTERN_THRESHOLD:
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                           'Friday', 'Saturday', 'Sunday']
                logger.info(
                    f"Weekly pattern detected: {day_names[most_common_day]} "
                    f"({most_common_count}/{total_releases} = {percentage:.1%})"
                )
                return most_common_day
            else:
                logger.debug(
                    f"No clear weekly pattern: highest is {percentage:.1%} "
                    f"(threshold: {self.WEEKLY_PATTERN_THRESHOLD:.1%})"
                )
                return None
                
        except Exception as e:
            logger.error(f"Error detecting weekly pattern: {e}")
            return None
    
    def calculate_confidence_score(self, chapter_dates: List[datetime]) -> float:
        """
        Calculate confidence in detected pattern (0.0-1.0).
        
        Confidence is based on:
        - Number of data points (more is better)
        - Consistency of intervals (lower variance is better)
        - Strength of weekly pattern if detected
        
        Args:
            chapter_dates: List of datetime objects
            
        Returns:
            Confidence score between 0.0 and 1.0
            
        Example:
            >>> analyzer = PatternAnalyzer()
            >>> # Regular weekly releases = high confidence
            >>> dates = [datetime(2024, 1, i) for i in range(1, 30, 7)]
            >>> score = analyzer.calculate_confidence_score(dates)
            >>> score > 0.7
            True
        """
        if not chapter_dates or len(chapter_dates) < self.MIN_RELEASES_FOR_CONFIDENCE:
            return 0.0
        
        try:
            confidence_factors = []
            
            # Factor 1: Data quantity (more releases = higher confidence)
            # Scale: 3 releases = 0.3, 10+ releases = 1.0
            data_quantity_score = min(len(chapter_dates) / 10.0, 1.0)
            confidence_factors.append(data_quantity_score)
            
            # Factor 2: Weekly pattern strength
            distribution = self.get_day_of_week_distribution(chapter_dates)
            if distribution:
                total_releases = len(chapter_dates)
                max_day_count = max(distribution.values())
                pattern_strength = max_day_count / total_releases
                confidence_factors.append(pattern_strength)
            
            # Factor 3: Interval consistency (low variance = high confidence)
            if len(chapter_dates) >= 3:
                sorted_dates = sorted(chapter_dates, reverse=True)
                intervals = []
                for i in range(len(sorted_dates) - 1):
                    interval_days = (sorted_dates[i] - sorted_dates[i + 1]).total_seconds() / 86400
                    intervals.append(interval_days)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    # Calculate coefficient of variation (CV)
                    if avg_interval > 0:
                        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                        std_dev = variance ** 0.5
                        cv = std_dev / avg_interval
                        # Convert CV to confidence score (lower CV = higher confidence)
                        # CV of 0 = 1.0, CV of 1.0 = 0.0
                        consistency_score = max(0.0, 1.0 - cv)
                        confidence_factors.append(consistency_score)
            
            # Calculate overall confidence as average of factors
            if confidence_factors:
                overall_confidence = sum(confidence_factors) / len(confidence_factors)
                logger.debug(
                    f"Confidence score: {overall_confidence:.2f} "
                    f"(factors: {[f'{f:.2f}' for f in confidence_factors]})"
                )
                return round(overall_confidence, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {e}")
            return 0.0
    
    def predict_next_release_date(self, chapter_dates: List[datetime], 
                                  current_date: Optional[datetime] = None) -> Optional[datetime]:
        """
        Predict when next chapter might be released using detected patterns.
        
        This method uses either weekly pattern or average interval to predict
        the next release date. It's used for informational purposes and to
        optimize scraping schedules.
        
        Args:
            chapter_dates: List of datetime objects (sorted, newest first)
            current_date: Reference date for prediction (defaults to now)
            
        Returns:
            Predicted datetime of next release or None if insufficient data
            
        Example:
            >>> analyzer = PatternAnalyzer()
            >>> dates = [
            ...     datetime(2024, 1, 15),  # Monday
            ...     datetime(2024, 1, 8),   # Monday
            ...     datetime(2024, 1, 1)    # Monday
            ... ]
            >>> next_date = analyzer.predict_next_release_date(dates)
            >>> next_date.weekday()  # Should be Monday (0)
            0
        """
        if not chapter_dates:
            logger.debug("No chapter dates provided for prediction")
            return None
        
        if current_date is None:
            current_date = datetime.now()
        
        try:
            # Sort dates to ensure newest first
            sorted_dates = sorted(chapter_dates, reverse=True)
            most_recent_release = sorted_dates[0]
            
            # Try weekly pattern first
            preferred_day = self.detect_weekly_pattern(chapter_dates)
            
            if preferred_day is not None:
                # Find next occurrence of preferred day after most recent release
                days_ahead = (preferred_day - most_recent_release.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week if same day
                
                predicted_date = most_recent_release + timedelta(days=days_ahead)
                
                # If predicted date is in the past, move to next week
                while predicted_date < current_date:
                    predicted_date += timedelta(days=7)
                
                logger.info(
                    f"Predicted next release (weekly pattern): {predicted_date.strftime('%Y-%m-%d %A')}"
                )
                return predicted_date
            
            # Fall back to average interval
            avg_interval = self.calculate_average_interval(chapter_dates)
            
            if avg_interval is not None:
                predicted_date = most_recent_release + timedelta(days=avg_interval)
                
                # If predicted date is in the past, use current date + interval
                if predicted_date < current_date:
                    predicted_date = current_date + timedelta(days=avg_interval)
                
                logger.info(
                    f"Predicted next release (average interval): "
                    f"{predicted_date.strftime('%Y-%m-%d')} "
                    f"({avg_interval:.1f} days from last release)"
                )
                return predicted_date
            
            logger.debug("Insufficient data for prediction")
            return None
            
        except Exception as e:
            logger.error(f"Error predicting next release date: {e}")
            return None
    
    def analyze_pattern_changes(self, old_dates: List[datetime], 
                                new_dates: List[datetime]) -> bool:
        """
        Detect if release pattern has changed significantly.
        
        This method compares old and new pattern analysis to determine if
        the schedule should be recalculated. Used for requirement 4.5.
        
        Args:
            old_dates: Previous chapter dates used for pattern detection
            new_dates: Updated chapter dates including new releases
            
        Returns:
            True if pattern has changed significantly, False otherwise
        """
        if not old_dates or not new_dates:
            return False
        
        try:
            # Only check if we have enough new data
            if len(new_dates) < 10:
                return False
            
            # Compare weekly patterns
            old_pattern = self.detect_weekly_pattern(old_dates)
            new_pattern = self.detect_weekly_pattern(new_dates)
            
            if old_pattern != new_pattern:
                logger.info(
                    f"Weekly pattern changed: {old_pattern} -> {new_pattern}"
                )
                return True
            
            # Compare average intervals (significant if >20% change)
            old_avg = self.calculate_average_interval(old_dates)
            new_avg = self.calculate_average_interval(new_dates)
            
            if old_avg and new_avg:
                change_percentage = abs(new_avg - old_avg) / old_avg
                if change_percentage > 0.20:
                    logger.info(
                        f"Average interval changed significantly: "
                        f"{old_avg:.1f} -> {new_avg:.1f} days ({change_percentage:.1%})"
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error analyzing pattern changes: {e}")
            return False
    
    def get_pattern_summary(self, chapter_dates: List[datetime]) -> Dict:
        """
        Get a comprehensive summary of detected patterns.
        
        This is a convenience method that runs all analysis methods and
        returns a dictionary with all pattern information.
        
        Args:
            chapter_dates: List of datetime objects
            
        Returns:
            Dictionary with pattern analysis results
        """
        if not chapter_dates:
            return {
                'has_data': False,
                'release_count': 0
            }
        
        try:
            summary = {
                'has_data': True,
                'release_count': len(chapter_dates),
                'average_interval_days': self.calculate_average_interval(chapter_dates),
                'preferred_release_day': self.detect_weekly_pattern(chapter_dates),
                'confidence_score': self.calculate_confidence_score(chapter_dates),
                'predicted_next_release': self.predict_next_release_date(chapter_dates),
                'day_distribution': self.get_day_of_week_distribution(chapter_dates)
            }
            
            # Add human-readable day name if pattern detected
            if summary['preferred_release_day'] is not None:
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                           'Friday', 'Saturday', 'Sunday']
                summary['preferred_release_day_name'] = day_names[summary['preferred_release_day']]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating pattern summary: {e}")
            return {'has_data': False, 'error': str(e)}
