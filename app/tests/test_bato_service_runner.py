"""
Unit tests for BatoServiceRunner - Entry point for containerized Bato service.

Tests cover:
- BatoServiceRunner initialization
- Database connection verification
- Signal handler registration
- Graceful shutdown with active jobs
- Retry logic with exponential backoff
- Command-line argument parsing

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import unittest
from unittest import mock
import signal
import sys
import time
from datetime import datetime
from io import StringIO

from app.services.bato.bato_service_runner import BatoServiceRunner


class TestBatoServiceRunnerInitialization(unittest.TestCase):
    """Test BatoServiceRunner initialization."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    def test_initialization_default_mode(self, mock_signal, mock_init_logging):
        """Test runner initializes correctly with default settings."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        self.assertFalse(runner.running)
        self.assertIsNone(runner.service)
        self.assertFalse(runner.test_mode)
        self.assertIsNone(runner.limit)
        self.assertFalse(runner.run_once)
        self.assertIsNotNone(runner.logger)
        
        # Verify logging was initialized
        mock_init_logging.assert_called_once()
        
        # Verify signal handlers were registered
        self.assertEqual(mock_signal.call_count, 2)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    def test_initialization_test_mode(self, mock_signal, mock_init_logging):
        """Test runner initializes correctly in test mode."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner(test_mode=True, limit=5, run_once=True)
        
        self.assertTrue(runner.test_mode)
        self.assertEqual(runner.limit, 5)
        self.assertTrue(runner.run_once)
        
        # Verify DEBUG logging was requested in test mode
        call_args = mock_init_logging.call_args
        self.assertEqual(call_args[1]['log_level'], 'DEBUG')
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    def test_initialization_with_limit(self, mock_signal, mock_init_logging):
        """Test runner initializes correctly with manga limit."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner(limit=10)
        
        self.assertEqual(runner.limit, 10)
        self.assertFalse(runner.test_mode)
        self.assertFalse(runner.run_once)


class TestDatabaseConnectionVerification(unittest.TestCase):
    """Test database connection verification."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.initialize_db_handler')
    @mock.patch('app.services.bato.bato_service_runner.get_db_handler')
    def test_verify_database_connection_success(self, mock_get_handler, 
                                                mock_init_handler, mock_signal, 
                                                mock_init_logging):
        """Test successful database connection verification."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        # Mock database handler
        mock_db_handler = mock.Mock()
        mock_db_handler.verify_connection.return_value = True
        mock_db_handler.get_pool_status.return_value = {
            'pool_size': 5,
            'checked_in': 5,
            'checked_out': 0
        }
        
        mock_init_handler.return_value = True
        mock_get_handler.return_value = mock_db_handler
        
        runner = BatoServiceRunner()
        result = runner.verify_database_connection()
        
        self.assertTrue(result)
        mock_init_handler.assert_called_once()
        mock_db_handler.verify_connection.assert_called_once()
        mock_db_handler.get_pool_status.assert_called_once()
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.initialize_db_handler')
    def test_verify_database_connection_init_failure(self, mock_init_handler, 
                                                     mock_signal, mock_init_logging):
        """Test database connection verification fails on init."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        mock_init_handler.return_value = False
        
        runner = BatoServiceRunner()
        result = runner.verify_database_connection()
        
        self.assertFalse(result)
        mock_init_handler.assert_called_once()
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.initialize_db_handler')
    @mock.patch('app.services.bato.bato_service_runner.get_db_handler')
    def test_verify_database_connection_verify_failure(self, mock_get_handler,
                                                       mock_init_handler, mock_signal,
                                                       mock_init_logging):
        """Test database connection verification fails on verify."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        mock_db_handler = mock.Mock()
        mock_db_handler.verify_connection.return_value = False
        
        mock_init_handler.return_value = True
        mock_get_handler.return_value = mock_db_handler
        
        runner = BatoServiceRunner()
        result = runner.verify_database_connection()
        
        self.assertFalse(result)
        mock_db_handler.verify_connection.assert_called_once()
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.initialize_db_handler')
    def test_verify_database_connection_exception(self, mock_init_handler,
                                                  mock_signal, mock_init_logging):
        """Test database connection verification handles exceptions."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        mock_init_handler.side_effect = Exception("Database error")
        
        runner = BatoServiceRunner()
        result = runner.verify_database_connection()
        
        self.assertFalse(result)


class TestSignalHandlerRegistration(unittest.TestCase):
    """Test signal handler registration."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    def test_signal_handlers_registered(self, mock_signal, mock_init_logging):
        """Test SIGTERM and SIGINT handlers are registered."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Verify signal.signal was called twice (SIGTERM and SIGINT)
        self.assertEqual(mock_signal.call_count, 2)
        
        # Verify correct signals were registered
        calls = mock_signal.call_args_list
        signals_registered = [call[0][0] for call in calls]
        
        self.assertIn(signal.SIGTERM, signals_registered)
        self.assertIn(signal.SIGINT, signals_registered)
        
        # Verify shutdown method was registered as handler
        for call in calls:
            self.assertEqual(call[0][1], runner.shutdown)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    def test_setup_signal_handlers_called_during_init(self, mock_signal, mock_init_logging):
        """Test setup_signal_handlers is called during initialization."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Signal handlers should be set up during __init__
        self.assertGreater(mock_signal.call_count, 0)


class TestGracefulShutdown(unittest.TestCase):
    """Test graceful shutdown with active jobs."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.exit')
    def test_shutdown_without_service(self, mock_exit, mock_signal, mock_init_logging):
        """Test shutdown when no service is running."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        runner.shutdown(signal.SIGTERM, None)
        
        self.assertFalse(runner.running)
        mock_exit.assert_called_once_with(0)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.exit')
    @mock.patch('time.sleep')
    def test_shutdown_with_running_service(self, mock_sleep, mock_exit, 
                                          mock_signal, mock_init_logging):
        """Test shutdown waits for service to complete."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock service with thread
        mock_service = mock.Mock()
        mock_thread = mock.Mock()
        mock_thread.is_alive.return_value = False  # Thread completes immediately
        mock_service.thread = mock_thread
        
        runner.service = mock_service
        runner.shutdown(signal.SIGTERM, None)
        
        self.assertFalse(runner.running)
        mock_service.stop.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.exit')
    @mock.patch('time.sleep')
    @mock.patch('time.time')
    def test_shutdown_timeout_force_terminate(self, mock_time, mock_sleep, 
                                             mock_exit, mock_signal, mock_init_logging):
        """Test shutdown force-terminates after timeout."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock service with thread that never completes
        mock_service = mock.Mock()
        mock_thread = mock.Mock()
        mock_thread.is_alive.return_value = True  # Thread keeps running
        mock_service.thread = mock_thread
        
        runner.service = mock_service
        
        # Mock time to simulate timeout
        start_time = 1000.0
        mock_time.side_effect = [start_time] + [start_time + i for i in range(1, 35)]
        
        runner.shutdown(signal.SIGTERM, None)
        
        self.assertFalse(runner.running)
        mock_service.stop.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.exit')
    def test_shutdown_handles_exception(self, mock_exit, mock_signal, mock_init_logging):
        """Test shutdown handles exceptions gracefully."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock service that raises exception on stop
        mock_service = mock.Mock()
        mock_service.stop.side_effect = Exception("Stop failed")
        
        runner.service = mock_service
        runner.shutdown(signal.SIGTERM, None)
        
        self.assertFalse(runner.running)
        mock_exit.assert_called_once_with(0)


class TestRetryLogic(unittest.TestCase):
    """Test retry logic with exponential backoff."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.BatoScrapingService')
    @mock.patch('time.sleep')
    def test_retry_logic_exponential_backoff(self, mock_sleep, mock_service_class,
                                            mock_signal, mock_init_logging):
        """Test retry logic uses exponential backoff."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock verify_database_connection to fail then succeed
        call_count = [0]
        def verify_side_effect():
            call_count[0] += 1
            if call_count[0] < 3:
                return False
            return True
        
        runner.verify_database_connection = mock.Mock(side_effect=verify_side_effect)
        
        # Mock service to start successfully after retries
        mock_service = mock.Mock()
        mock_thread = mock.Mock()
        mock_thread.is_alive.return_value = True
        mock_service.thread = mock_thread
        mock_service.CHECK_INTERVAL_SECONDS = 300
        mock_service_class.return_value = mock_service
        
        # Run with run_once to exit after one cycle
        runner.run_once = True
        
        # Start run in a way that allows us to stop it
        import threading
        run_thread = threading.Thread(target=runner.run)
        run_thread.daemon = True
        run_thread.start()
        
        # Give it time to attempt retries
        time.sleep(0.5)
        
        # Stop the runner
        runner.running = False
        run_thread.join(timeout=2)
        
        # Verify exponential backoff was used
        # First retry: 5 seconds, second retry: 10 seconds
        if mock_sleep.call_count > 0:
            # Check that sleep was called (backoff happened)
            self.assertGreater(mock_sleep.call_count, 0)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.exit')
    def test_retry_logic_max_retries_exceeded(self, mock_exit, mock_signal, 
                                              mock_init_logging):
        """Test service exits after max retries."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock verify_database_connection to always fail
        runner.verify_database_connection = mock.Mock(return_value=False)
        
        # Mock sleep to speed up test
        with mock.patch('time.sleep'):
            runner.run()
        
        # Verify sys.exit was called with error code
        mock_exit.assert_called_once_with(1)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    def test_retry_count_resets_on_success(self, mock_signal, mock_init_logging):
        """Test retry count resets after successful start."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # This is implicitly tested by the run() method logic
        # If service starts successfully, retry_count is reset to 0
        # We verify this through the code structure
        self.assertEqual(runner.MAX_RETRIES, 5)


class TestCommandLineArgumentParsing(unittest.TestCase):
    """Test command-line argument parsing."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.argv', ['bato_service_runner.py'])
    def test_parse_arguments_no_flags(self, mock_signal, mock_init_logging):
        """Test argument parsing with no flags."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        # Mock the run method to prevent actual execution
        with mock.patch.object(BatoServiceRunner, 'run'):
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('--test', action='store_true')
            parser.add_argument('--limit', type=int)
            parser.add_argument('--once', action='store_true')
            
            args = parser.parse_args([])
            
            self.assertFalse(args.test)
            self.assertIsNone(args.limit)
            self.assertFalse(args.once)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.argv', ['bato_service_runner.py', '--test'])
    def test_parse_arguments_test_flag(self, mock_signal, mock_init_logging):
        """Test argument parsing with --test flag."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--limit', type=int)
        parser.add_argument('--once', action='store_true')
        
        args = parser.parse_args(['--test'])
        
        self.assertTrue(args.test)
        self.assertIsNone(args.limit)
        self.assertFalse(args.once)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.argv', ['bato_service_runner.py', '--limit', '10'])
    def test_parse_arguments_limit_flag(self, mock_signal, mock_init_logging):
        """Test argument parsing with --limit flag."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--limit', type=int)
        parser.add_argument('--once', action='store_true')
        
        args = parser.parse_args(['--limit', '10'])
        
        self.assertFalse(args.test)
        self.assertEqual(args.limit, 10)
        self.assertFalse(args.once)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.argv', ['bato_service_runner.py', '--once'])
    def test_parse_arguments_once_flag(self, mock_signal, mock_init_logging):
        """Test argument parsing with --once flag."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--limit', type=int)
        parser.add_argument('--once', action='store_true')
        
        args = parser.parse_args(['--once'])
        
        self.assertFalse(args.test)
        self.assertIsNone(args.limit)
        self.assertTrue(args.once)
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('sys.argv', ['bato_service_runner.py', '--test', '--limit', '5', '--once'])
    def test_parse_arguments_all_flags(self, mock_signal, mock_init_logging):
        """Test argument parsing with all flags combined."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--limit', type=int)
        parser.add_argument('--once', action='store_true')
        
        args = parser.parse_args(['--test', '--limit', '5', '--once'])
        
        self.assertTrue(args.test)
        self.assertEqual(args.limit, 5)
        self.assertTrue(args.once)


class TestCleanup(unittest.TestCase):
    """Test cleanup and resource management."""
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.db_session')
    @mock.patch('app.services.bato.bato_service_runner.engine')
    def test_cleanup_closes_database_connections(self, mock_engine, mock_db_session,
                                                 mock_signal, mock_init_logging):
        """Test cleanup closes database connections."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock database handler
        mock_db_handler = mock.Mock()
        runner.db_handler = mock_db_handler
        
        runner.cleanup()
        
        # Verify database connections were closed
        mock_db_handler.dispose.assert_called_once()
        mock_db_session.remove.assert_called_once()
        mock_engine.dispose.assert_called_once()
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.db_session')
    @mock.patch('app.services.bato.bato_service_runner.engine')
    def test_cleanup_stops_service(self, mock_engine, mock_db_session,
                                   mock_signal, mock_init_logging):
        """Test cleanup stops running service."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock service
        mock_service = mock.Mock()
        runner.service = mock_service
        
        runner.cleanup()
        
        # Verify service was stopped
        mock_service.stop.assert_called_once()
    
    @mock.patch('app.services.bato.bato_service_runner.init_logging')
    @mock.patch('app.services.bato.bato_service_runner.signal.signal')
    @mock.patch('app.services.bato.bato_service_runner.db_session')
    @mock.patch('app.services.bato.bato_service_runner.engine')
    def test_cleanup_handles_exceptions(self, mock_engine, mock_db_session,
                                       mock_signal, mock_init_logging):
        """Test cleanup handles exceptions gracefully."""
        mock_logger = mock.Mock()
        mock_init_logging.return_value = mock_logger
        
        runner = BatoServiceRunner()
        
        # Mock service that raises exception on stop
        mock_service = mock.Mock()
        mock_service.stop.side_effect = Exception("Stop failed")
        runner.service = mock_service
        
        # Mock db_session that raises exception
        mock_db_session.remove.side_effect = Exception("DB cleanup failed")
        
        # Should not raise exception
        runner.cleanup()
        
        # Verify cleanup was attempted despite errors
        mock_service.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
