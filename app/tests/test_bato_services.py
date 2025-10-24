"""
Unit tests for Bato notification system core components.

Tests cover:
- PatternAnalyzer: weekly detection, average interval, confidence
- SchedulingEngine: interval calculation, min/max enforcement
- ChapterComparator: new chapter detection, batch logic
- NotificationManager: notification creation, importance levels
"""

import unittest
from unittest import mock
from datetime import datetime, timedelta
from app.services.bato.pattern_analyzer import PatternAnalyzer
from app.services.bato.scheduling_engine import SchedulingEngine
from app.services.bato.chapter_comparator import ChapterComparator
from app.services.bato.notification_manager import NotificationManager


class TestPatternAnalyzer(unittest.TestCase):
    """Test PatternAnalyzer service for release pattern detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = PatternAnalyzer()
    
    def test_calculate_average_interval_with_valid_data(self):
        """Test average interval calculation with regular releases."""
        # Weekly releases (7 days apart)
        dates = [
            datetime(2024, 1, 22),
            datetime(2024, 1, 15),
            datetime(2024, 1, 8),
            datetime(2024, 1, 1)
        ]
        
        avg_interval = self.analyzer.calculate_average_interval(dates)
        
        self.assertIsNotNone(avg_interval)
        self.assertAlmostEqual(avg_interval, 7.0, places=1)
    
    def test_calculate_average_interval_with_irregular_data(self):
        """Test average interval calculation with irregular releases."""
        dates = [
            datetime(2024, 1, 20),  # 5 days
            datetime(2024, 1, 15),  # 10 days
            datetime(2024, 1, 5),   # 3 days
            datetime(2024, 1, 2)
        ]
        
        avg_interval = self.analyzer.calculate_average_interval(dates)
        
        self.assertIsNotNone(avg_interval)
        # Average of 5, 10, 3 = 6.0
        self.assertAlmostEqual(avg_interval, 6.0, places=1)
    
    def test_calculate_average_interval_insufficient_data(self):
        """Test average interval returns None with insufficient data."""
        # Only one date
        dates = [datetime(2024, 1, 1)]
        
        avg_interval = self.analyzer.calculate_average_interval(dates)
        
        self.assertIsNone(avg_interval)
    
    def test_calculate_average_interval_empty_list(self):
        """Test average interval returns None with empty list."""
        avg_interval = self.analyzer.calculate_average_interval([])
        
        self.assertIsNone(avg_interval)
    
    def test_detect_weekly_pattern_strong_pattern(self):
        """Test weekly pattern detection with strong Monday pattern (80%)."""
        # 4 out of 5 releases on Monday (80% > 60% threshold)
        dates = [
            datetime(2024, 1, 22),  # Monday
            datetime(2024, 1, 15),  # Monday
            datetime(2024, 1, 10),  # Wednesday
            datetime(2024, 1, 8),   # Monday
            datetime(2024, 1, 1)    # Monday
        ]
        
        preferred_day = self.analyzer.detect_weekly_pattern(dates)
        
        self.assertIsNotNone(preferred_day)
        self.assertEqual(preferred_day, 0)  # Monday = 0
    
    def test_detect_weekly_pattern_weak_pattern(self):
        """Test weekly pattern detection with weak pattern (below threshold)."""
        # Evenly distributed across days
        dates = [
            datetime(2024, 1, 22),  # Monday
            datetime(2024, 1, 23),  # Tuesday
            datetime(2024, 1, 24),  # Wednesday
            datetime(2024, 1, 25),  # Thursday
            datetime(2024, 1, 26)   # Friday
        ]
        
        preferred_day = self.analyzer.detect_weekly_pattern(dates)
        
        self.assertIsNone(preferred_day)
    
    def test_detect_weekly_pattern_insufficient_data(self):
        """Test weekly pattern returns None with insufficient data."""
        # Only 4 releases (need 5)
        dates = [
            datetime(2024, 1, 22),
            datetime(2024, 1, 15),
            datetime(2024, 1, 8),
            datetime(2024, 1, 1)
        ]
        
        preferred_day = self.analyzer.detect_weekly_pattern(dates)
        
        self.assertIsNone(preferred_day)
    
    def test_calculate_confidence_score_high_confidence(self):
        """Test confidence score with regular weekly releases."""
        # Regular weekly releases = high confidence
        dates = [
            datetime(2024, 1, 29),
            datetime(2024, 1, 22),
            datetime(2024, 1, 15),
            datetime(2024, 1, 8),
            datetime(2024, 1, 1)
        ]
        
        confidence = self.analyzer.calculate_confidence_score(dates)
        
        self.assertGreater(confidence, 0.5)
        self.assertLessEqual(confidence, 1.0)
    
    def test_calculate_confidence_score_low_confidence(self):
        """Test confidence score with irregular releases."""
        # Irregular releases = lower confidence
        dates = [
            datetime(2024, 1, 25),
            datetime(2024, 1, 20),
            datetime(2024, 1, 5)
        ]
        
        confidence = self.analyzer.calculate_confidence_score(dates)
        
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLess(confidence, 0.7)
    
    def test_calculate_confidence_score_insufficient_data(self):
        """Test confidence score returns 0.0 with insufficient data."""
        dates = [datetime(2024, 1, 1), datetime(2024, 1, 2)]
        
        confidence = self.analyzer.calculate_confidence_score(dates)
        
        self.assertEqual(confidence, 0.0)
    
    def test_get_day_of_week_distribution(self):
        """Test day of week distribution calculation."""
        dates = [
            datetime(2024, 1, 22),  # Monday
            datetime(2024, 1, 15),  # Monday
            datetime(2024, 1, 10),  # Wednesday
            datetime(2024, 1, 8)    # Monday
        ]
        
        distribution = self.analyzer.get_day_of_week_distribution(dates)
        
        self.assertEqual(distribution[0], 3)  # 3 Mondays
        self.assertEqual(distribution[2], 1)  # 1 Wednesday
    
    def test_predict_next_release_date_with_weekly_pattern(self):
        """Test next release prediction with weekly pattern."""
        # Strong Monday pattern
        dates = [
            datetime(2024, 1, 22),  # Monday
            datetime(2024, 1, 15),  # Monday
            datetime(2024, 1, 8),   # Monday
            datetime(2024, 1, 1),   # Monday
            datetime(2023, 12, 25)  # Monday
        ]
        
        current_date = datetime(2024, 1, 23)  # Tuesday
        predicted = self.analyzer.predict_next_release_date(dates, current_date)
        
        self.assertIsNotNone(predicted)
        self.assertEqual(predicted.weekday(), 0)  # Should be Monday
        self.assertGreater(predicted, current_date)
    
    def test_predict_next_release_date_with_average_interval(self):
        """Test next release prediction using average interval."""
        # No clear weekly pattern, but regular 5-day intervals
        dates = [
            datetime(2024, 1, 20),
            datetime(2024, 1, 15),
            datetime(2024, 1, 10),
            datetime(2024, 1, 5)
        ]
        
        current_date = datetime(2024, 1, 21)
        predicted = self.analyzer.predict_next_release_date(dates, current_date)
        
        self.assertIsNotNone(predicted)
        self.assertGreater(predicted, current_date)


class TestSchedulingEngine(unittest.TestCase):
    """Test SchedulingEngine service for optimal scraping schedules."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = SchedulingEngine()
    
    @mock.patch('app.services.bato.scheduling_engine.BatoRepository')
    def test_calculate_next_scrape_time_default_interval(self, mock_repo_class):
        """Test default 24h interval for new manga with no data."""
        mock_repo = mock_repo_class.return_value
        mock_repo.get_manga_details.return_value = mock.Mock(upload_status='ongoing')
        mock_repo.get_schedule.return_value = None
        mock_repo.get_chapter_dates.return_value = []
        
        self.engine.repository = mock_repo
        
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        next_scrape = self.engine.calculate_next_scrape_time(123456, current_time)
        
        expected_time = current_time + timedelta(hours=24)
        self.assertEqual(next_scrape, expected_time)
    
    @mock.patch('app.services.bato.scheduling_engine.BatoRepository')
    def test_calculate_next_scrape_time_completed_status(self, mock_repo_class):
        """Test 30-day interval for completed manga."""
        mock_repo = mock_repo_class.return_value
        mock_repo.get_manga_details.return_value = mock.Mock(upload_status='completed')
        
        self.engine.repository = mock_repo
        
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        next_scrape = self.engine.calculate_next_scrape_time(123456, current_time)
        
        expected_time = current_time + timedelta(days=30)
        self.assertEqual(next_scrape, expected_time)
    
    @mock.patch('app.services.bato.scheduling_engine.BatoRepository')
    def test_calculate_next_scrape_time_dropped_status(self, mock_repo_class):
        """Test 30-day interval for dropped manga."""
        mock_repo = mock_repo_class.return_value
        mock_repo.get_manga_details.return_value = mock.Mock(upload_status='dropped')
        
        self.engine.repository = mock_repo
        
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        next_scrape = self.engine.calculate_next_scrape_time(123456, current_time)
        
        expected_time = current_time + timedelta(days=30)
        self.assertEqual(next_scrape, expected_time)
    
    def test_enforce_interval_constraints_minimum(self):
        """Test minimum interval enforcement (6 hours)."""
        # Try to set 3 hours (below minimum)
        constrained = self.engine._enforce_interval_constraints(3.0)
        
        self.assertEqual(constrained, 6.0)
    
    def test_enforce_interval_constraints_maximum(self):
        """Test maximum interval enforcement (14 days = 336 hours)."""
        # Try to set 20 days (above maximum)
        constrained = self.engine._enforce_interval_constraints(480.0)
        
        self.assertEqual(constrained, 336.0)  # 14 days * 24 hours
    
    def test_enforce_interval_constraints_within_range(self):
        """Test interval within valid range is unchanged."""
        # 48 hours is within 6h - 336h range
        constrained = self.engine._enforce_interval_constraints(48.0)
        
        self.assertEqual(constrained, 48.0)
    
    def test_apply_no_update_penalty_single(self):
        """Test no-update penalty with one consecutive no-update."""
        base_interval = 24.0
        adjusted = self.engine._apply_no_update_penalty(base_interval, 1)
        
        # Should be 24 * 1.5 = 36
        self.assertEqual(adjusted, 36.0)
    
    def test_apply_no_update_penalty_multiple(self):
        """Test no-update penalty with multiple consecutive no-updates."""
        base_interval = 24.0
        adjusted = self.engine._apply_no_update_penalty(base_interval, 2)
        
        # Should be 24 * 1.5^2 = 54
        self.assertEqual(adjusted, 54.0)
    
    def test_apply_no_update_penalty_capped(self):
        """Test no-update penalty is capped at 3 increases."""
        base_interval = 24.0
        adjusted_3 = self.engine._apply_no_update_penalty(base_interval, 3)
        adjusted_5 = self.engine._apply_no_update_penalty(base_interval, 5)
        
        # Both should be capped at 3 increases
        self.assertEqual(adjusted_3, adjusted_5)
    
    @mock.patch('app.services.bato.scheduling_engine.BatoRepository')
    def test_create_initial_schedule(self, mock_repo_class):
        """Test creating initial schedule with 24h default."""
        mock_repo = mock_repo_class.return_value
        mock_repo.upsert_schedule.return_value = True
        
        self.engine.repository = mock_repo
        
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        result = self.engine.create_initial_schedule(
            123456, 
            'https://bato.to/series/123', 
            current_time
        )
        
        self.assertTrue(result)
        
        # Verify upsert_schedule was called with correct data
        call_args = mock_repo.upsert_schedule.call_args[0][0]
        self.assertEqual(call_args['scraping_interval_hours'], 24)
        self.assertEqual(call_args['anilist_id'], 123456)


class TestChapterComparator(unittest.TestCase):
    """Test ChapterComparator service for new chapter detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.comparator = ChapterComparator()
    
    @mock.patch('app.services.bato.chapter_comparator.BatoRepository')
    def test_find_new_chapters_all_new(self, mock_repo_class):
        """Test finding new chapters when all are new."""
        mock_repo = mock_repo_class.return_value
        mock_repo.get_existing_chapter_ids.return_value = set()
        
        self.comparator.repository = mock_repo
        
        scraped = [
            {'bato_chapter_id': '2068065', 'dname': 'Chapter 112'},
            {'bato_chapter_id': '2068066', 'dname': 'Chapter 113'}
        ]
        
        new_chapters = self.comparator.find_new_chapters(123456, scraped)
        
        self.assertEqual(len(new_chapters), 2)
    
    @mock.patch('app.services.bato.chapter_comparator.BatoRepository')
    def test_find_new_chapters_some_existing(self, mock_repo_class):
        """Test finding new chapters when some already exist."""
        mock_repo = mock_repo_class.return_value
        mock_repo.get_existing_chapter_ids.return_value = {'2068065'}
        
        self.comparator.repository = mock_repo
        
        scraped = [
            {'bato_chapter_id': '2068065', 'dname': 'Chapter 112'},  # Exists
            {'bato_chapter_id': '2068066', 'dname': 'Chapter 113'}   # New
        ]
        
        new_chapters = self.comparator.find_new_chapters(123456, scraped)
        
        self.assertEqual(len(new_chapters), 1)
        self.assertEqual(new_chapters[0]['bato_chapter_id'], '2068066')
    
    @mock.patch('app.services.bato.chapter_comparator.BatoRepository')
    def test_find_new_chapters_none_new(self, mock_repo_class):
        """Test finding new chapters when all already exist."""
        mock_repo = mock_repo_class.return_value
        mock_repo.get_existing_chapter_ids.return_value = {'2068065', '2068066'}
        
        self.comparator.repository = mock_repo
        
        scraped = [
            {'bato_chapter_id': '2068065', 'dname': 'Chapter 112'},
            {'bato_chapter_id': '2068066', 'dname': 'Chapter 113'}
        ]
        
        new_chapters = self.comparator.find_new_chapters(123456, scraped)
        
        self.assertEqual(len(new_chapters), 0)
    
    def test_should_create_batch_notification_true(self):
        """Test batch notification logic with 3+ chapters."""
        chapters = [
            {'bato_chapter_id': '1'},
            {'bato_chapter_id': '2'},
            {'bato_chapter_id': '3'}
        ]
        
        is_batch = self.comparator.should_create_batch_notification(chapters)
        
        self.assertTrue(is_batch)
    
    def test_should_create_batch_notification_false(self):
        """Test batch notification logic with less than 3 chapters."""
        chapters = [
            {'bato_chapter_id': '1'},
            {'bato_chapter_id': '2'}
        ]
        
        is_batch = self.comparator.should_create_batch_notification(chapters)
        
        self.assertFalse(is_batch)
    
    def test_validate_chapter_data_valid(self):
        """Test chapter validation with valid data."""
        chapter = {
            'bato_chapter_id': '2068065',
            'chapter_number': 112,
            'dname': 'Chapter 112',
            'full_url': 'https://bato.to/chapter/2068065'
        }
        
        is_valid = self.comparator.validate_chapter_data(chapter)
        
        self.assertTrue(is_valid)
    
    def test_validate_chapter_data_missing_field(self):
        """Test chapter validation with missing required field."""
        chapter = {
            'bato_chapter_id': '2068065',
            'chapter_number': 112,
            # Missing 'dname' and 'full_url'
        }
        
        is_valid = self.comparator.validate_chapter_data(chapter)
        
        self.assertFalse(is_valid)
    
    def test_filter_valid_chapters(self):
        """Test filtering out invalid chapters."""
        chapters = [
            {
                'bato_chapter_id': '1',
                'chapter_number': 1,
                'dname': 'Chapter 1',
                'full_url': 'https://bato.to/chapter/1'
            },
            {
                'bato_chapter_id': '2',
                # Missing required fields
            },
            {
                'bato_chapter_id': '3',
                'chapter_number': 3,
                'dname': 'Chapter 3',
                'full_url': 'https://bato.to/chapter/3'
            }
        ]
        
        valid = self.comparator.filter_valid_chapters(chapters)
        
        self.assertEqual(len(valid), 2)
        self.assertEqual(valid[0]['bato_chapter_id'], '1')
        self.assertEqual(valid[1]['bato_chapter_id'], '3')
    
    def test_get_chapter_summary_single(self):
        """Test chapter summary for single chapter."""
        chapters = [{'dname': 'Chapter 112'}]
        
        summary = self.comparator.get_chapter_summary(chapters)
        
        self.assertEqual(summary, 'Chapter 112')
    
    def test_get_chapter_summary_multiple(self):
        """Test chapter summary for multiple chapters."""
        chapters = [
            {'dname': 'Chapter 112'},
            {'dname': 'Chapter 113'},
            {'dname': 'Chapter 114'},
            {'dname': 'Chapter 115'}
        ]
        
        summary = self.comparator.get_chapter_summary(chapters)
        
        self.assertIn('Chapter 112', summary)
        self.assertIn('Chapter 115', summary)
        self.assertIn('4 chapters', summary)


class TestNotificationManager(unittest.TestCase):
    """Test NotificationManager service for notification creation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = NotificationManager()
    
    @mock.patch('app.services.bato.notification_manager.BatoRepository')
    def test_create_new_chapter_notification(self, mock_repo_class):
        """Test creating single chapter notification with importance 1."""
        mock_repo = mock_repo_class.return_value
        mock_notification = mock.Mock()
        mock_notification.id = 1
        mock_notification.anilist_id = 123456
        mock_notification.manga_name = 'Test Manga'
        mock_notification.message = 'New chapter available: Chapter 112'
        mock_notification.chapter_full_url = 'https://bato.to/chapter/2068065'
        mock_notification.importance = 1
        mock_notification.created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_repo.create_notification.return_value = mock_notification
        
        self.manager.repository = mock_repo
        
        chapter_data = {
            'anilist_id': 123456,
            'bato_link': 'https://bato.to/series/123',
            'manga_name': 'Test Manga',
            'chapter_id': 1,
            'chapter_dname': 'Chapter 112',
            'chapter_full_url': 'https://bato.to/chapter/2068065'
        }
        
        result = self.manager.create_new_chapter_notification(chapter_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'new_chapter')
        
        # Verify importance level is 1
        call_args = mock_repo.create_notification.call_args[0][0]
        self.assertEqual(call_args['importance'], 1)
    
    @mock.patch('app.services.bato.notification_manager.BatoRepository')
    def test_create_batch_notification(self, mock_repo_class):
        """Test creating batch notification with importance 2."""
        mock_repo = mock_repo_class.return_value
        mock_notification = mock.Mock()
        mock_notification.id = 2
        mock_notification.anilist_id = 123456
        mock_notification.manga_name = 'Test Manga'
        mock_notification.message = '3 new chapters available: Chapter 112 - Chapter 114'
        mock_notification.chapter_full_url = 'https://bato.to/chapter/2068065'
        mock_notification.importance = 2
        mock_notification.created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_repo.create_notification.return_value = mock_notification
        
        self.manager.repository = mock_repo
        
        manga_data = {
            'anilist_id': 123456,
            'bato_link': 'https://bato.to/series/123',
            'manga_name': 'Test Manga'
        }
        
        chapters = [
            {'chapter_id': 1, 'chapter_dname': 'Chapter 112', 'chapter_full_url': 'https://bato.to/chapter/2068065'},
            {'chapter_id': 2, 'chapter_dname': 'Chapter 113', 'chapter_full_url': 'https://bato.to/chapter/2068066'},
            {'chapter_id': 3, 'chapter_dname': 'Chapter 114', 'chapter_full_url': 'https://bato.to/chapter/2068067'}
        ]
        
        result = self.manager.create_batch_notification(manga_data, chapters)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'batch_update')
        self.assertEqual(result['chapters_count'], 3)
        
        # Verify importance level is 2
        call_args = mock_repo.create_notification.call_args[0][0]
        self.assertEqual(call_args['importance'], 2)
    
    @mock.patch('app.services.bato.notification_manager.BatoRepository')
    def test_create_status_change_notification(self, mock_repo_class):
        """Test creating status change notification with importance 3."""
        mock_repo = mock_repo_class.return_value
        mock_notification = mock.Mock()
        mock_notification.id = 3
        mock_notification.anilist_id = 123456
        mock_notification.manga_name = 'Test Manga'
        mock_notification.message = "Status changed from 'ongoing' to 'completed'"
        mock_notification.importance = 3
        mock_notification.created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_repo.create_notification.return_value = mock_notification
        
        self.manager.repository = mock_repo
        
        manga_data = {
            'anilist_id': 123456,
            'bato_link': 'https://bato.to/series/123',
            'manga_name': 'Test Manga'
        }
        
        result = self.manager.create_status_change_notification(
            manga_data, 
            'ongoing', 
            'completed'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'status_change')
        self.assertEqual(result['old_status'], 'ongoing')
        self.assertEqual(result['new_status'], 'completed')
        
        # Verify importance level is 3
        call_args = mock_repo.create_notification.call_args[0][0]
        self.assertEqual(call_args['importance'], 3)
    
    @mock.patch('app.services.bato.notification_manager.BatoRepository')
    def test_create_new_chapter_notification_missing_fields(self, mock_repo_class):
        """Test notification creation fails with missing required fields."""
        mock_repo = mock_repo_class.return_value
        self.manager.repository = mock_repo
        
        # Missing 'manga_name'
        chapter_data = {
            'anilist_id': 123456,
            'bato_link': 'https://bato.to/series/123',
            'chapter_dname': 'Chapter 112',
            'chapter_full_url': 'https://bato.to/chapter/2068065'
        }
        
        result = self.manager.create_new_chapter_notification(chapter_data)
        
        self.assertIsNone(result)
    
    @mock.patch('app.services.bato.notification_manager.BatoRepository')
    def test_create_batch_notification_single_chapter_fallback(self, mock_repo_class):
        """Test batch notification falls back to single notification for 1 chapter."""
        mock_repo = mock_repo_class.return_value
        mock_notification = mock.Mock()
        mock_notification.id = 1
        mock_notification.anilist_id = 123456
        mock_notification.manga_name = 'Test Manga'
        mock_notification.message = 'New chapter available: Chapter 112'
        mock_notification.chapter_full_url = 'https://bato.to/chapter/2068065'
        mock_notification.importance = 1
        mock_notification.created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_repo.create_notification.return_value = mock_notification
        
        self.manager.repository = mock_repo
        
        manga_data = {
            'anilist_id': 123456,
            'bato_link': 'https://bato.to/series/123',
            'manga_name': 'Test Manga'
        }
        
        chapters = [
            {'chapter_id': 1, 'chapter_dname': 'Chapter 112', 'chapter_full_url': 'https://bato.to/chapter/2068065'}
        ]
        
        result = self.manager.create_batch_notification(manga_data, chapters)
        
        self.assertIsNotNone(result)
        # Should create single chapter notification instead
        self.assertEqual(result['type'], 'new_chapter')


if __name__ == '__main__':
    unittest.main()
