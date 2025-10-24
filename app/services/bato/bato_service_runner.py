"""
Bato Service Runner - Entry Point for Containerized Bato Scraping Service

This script serves as the main entry point for running the Bato scraping service
in a dedicated Docker container. It handles initialization, signal handling,
database connection verification, and graceful shutdown.

Requirements:
- 2.1: Standalone Python script as main process
- 2.2: Located at app/services/bato/bato_service_runner.py
- 2.3: Initialize logging for Bato service
- 2.4: Create and start BatoScrapingService
- 2.5: Handle graceful shutdown on SIGTERM/SIGINT
- 2.6: Log errors and continue running with retry logic
- 8.1-8.5: Graceful shutdown with 30-second timeout
- 10.1-10.5: Testing support with --test, --limit, --once flags
"""

import sys
import os
import signal
import time
import logging
import argparse
from datetime import datetime
from typing import Optional

# Add app directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.services.bato.bato_scraping_service import BatoScrapingService
from app.services.bato.logging_config import init_logging, log_heartbeat
from app.services.bato.database_connection_handler import (
    initialize_db_handler,
    get_db_handler,
    dispose_db_handler
)
from app.functions.class_mangalist import db_session, engine
from sqlalchemy import text


class BatoServiceRunner:
    """
    Main runner class for the Bato scraping service container.
    
    Handles:
    - Service initialization and lifecycle
    - Signal handling for graceful shutdown
    - Database connection verification
    - Error recovery with exponential backoff
    - Command-line argument parsing
    """
    
    # Configuration constants
    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 5  # seconds
    MAX_RETRY_DELAY = 300  # 5 minutes
    SHUTDOWN_TIMEOUT = 30  # seconds
    HEARTBEAT_INTERVAL = 300  # 5 minutes
    
    def __init__(self, test_mode: bool = False, limit: Optional[int] = None, 
                 run_once: bool = False):
        """
        Initialize the service runner.
        
        Args:
            test_mode: Run in test mode with detailed logging
            limit: Limit number of manga to process (for testing)
            run_once: Run a single scraping cycle then exit
        """
        self.running = False
        self.service: Optional[BatoScrapingService] = None
        self.test_mode = test_mode
        self.limit = limit
        self.run_once = run_once
        self.logger: Optional[logging.Logger] = None
        self.last_heartbeat = time.time()
        self.db_handler = None
        
        # Setup logging (Requirement 2.3)
        self.setup_logging()
        
        # Setup signal handlers (Requirement 2.5)
        self.setup_signal_handlers()
        
        self.logger.info("BatoServiceRunner initialized")
        if self.test_mode:
            self.logger.info("Running in TEST MODE")
        if self.limit:
            self.logger.info(f"Limiting to {self.limit} manga")
        if self.run_once:
            self.logger.info("Will run once and exit")
    
    def setup_logging(self):
        """
        Configure logging for the Bato service.
        
        Requirement 2.3: Initialize logging for Bato service
        """
        log_level = 'DEBUG' if self.test_mode else 'INFO'
        self.logger = init_logging(log_level=log_level, log_to_file=True)
        
        # Also configure root logger for other modules
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.logger.info("Logging configured successfully")
    
    def setup_signal_handlers(self):
        """
        Register signal handlers for graceful shutdown.
        
        Requirement 2.5: Handle SIGTERM/SIGINT signals
        Requirement 8.1: Stop accepting new jobs on SIGTERM
        """
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        
        self.logger.info("Signal handlers registered (SIGTERM, SIGINT)")
    
    def verify_database_connection(self) -> bool:
        """
        Verify database connectivity before starting service.
        
        Requirements:
        - 3.1: Connect using DATABASE_URI configuration
        - 3.4: Configure connection pooling
        - 3.5: Retry logic with exponential backoff
        - 10.5: Verify database connectivity before starting main loop
        
        Returns:
            True if database is accessible, False otherwise
        """
        self.logger.info("Initializing database connection handler...")
        
        try:
            # Initialize database handler with connection pooling (Requirements 3.1, 3.4)
            if not initialize_db_handler():
                self.logger.error("Failed to initialize database handler")
                return False
            
            self.db_handler = get_db_handler()
            
            # Verify connection with retry logic (Requirements 3.5, 10.5)
            if not self.db_handler.verify_connection():
                self.logger.error("Database connection verification failed")
                return False
            
            # Log connection pool status
            pool_status = self.db_handler.get_pool_status()
            self.logger.info(f"Database connection pool status: {pool_status}")
            
            self.logger.info("Database connection verified successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Database connection setup failed: {e}", exc_info=True)
            return False
    
    def run(self):
        """
        Main run loop with retry logic.
        
        Requirements:
        - 2.4: Create and start BatoScrapingService
        - 2.6: Implement retry logic with exponential backoff
        - 3.5: Retry logic with exponential backoff for database errors
        
        This method:
        1. Verifies database connection
        2. Creates and starts BatoScrapingService
        3. Monitors service health
        4. Handles errors with exponential backoff
        5. Implements graceful shutdown
        """
        self.logger.info("=" * 60)
        self.logger.info("Bato Scraping Service Container Starting")
        self.logger.info("=" * 60)
        
        retry_count = 0
        self.running = True
        
        while self.running and retry_count < self.MAX_RETRIES:
            try:
                # Verify database connection (Requirement 10.5)
                if not self.verify_database_connection():
                    raise Exception("Database connection verification failed")
                
                # Create and start service (Requirement 2.4)
                # Use standalone_mode=True for containerized deployment
                self.logger.info("Creating BatoScrapingService instance in standalone mode...")
                self.service = BatoScrapingService(standalone_mode=True)
                
                self.logger.info("Starting BatoScrapingService...")
                self.service.start()
                
                self.logger.info("BatoScrapingService started successfully")
                self.logger.info("Service is now running. Press Ctrl+C to stop.")
                
                # Reset retry count on successful start
                retry_count = 0
                
                # If run_once mode, wait for one cycle then exit
                if self.run_once:
                    self.logger.info("Run-once mode: waiting for one scraping cycle...")
                    # Wait for one full cycle (CHECK_INTERVAL_SECONDS + processing time)
                    time.sleep(self.service.CHECK_INTERVAL_SECONDS + 60)
                    self.logger.info("Run-once mode: cycle complete, shutting down...")
                    self.running = False
                    break
                
                # Main monitoring loop
                while self.running:
                    time.sleep(10)  # Check every 10 seconds
                    
                    # Log heartbeat (Requirements 4.4, 9.1)
                    current_time = time.time()
                    if current_time - self.last_heartbeat >= self.HEARTBEAT_INTERVAL:
                        # Get service status and log structured heartbeat
                        service_status = self.service.get_service_status() if self.service else {}
                        log_heartbeat(service_status)
                        self.last_heartbeat = current_time
                    
                    # Check if service thread is still alive
                    if self.service and self.service.thread:
                        if not self.service.thread.is_alive() and self.running:
                            self.logger.error("Service thread died unexpectedly")
                            raise Exception("Service thread terminated")
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                self.running = False
                break
                
            except Exception as e:
                retry_count += 1
                self.logger.error(
                    f"Service error (attempt {retry_count}/{self.MAX_RETRIES}): {e}",
                    exc_info=True
                )
                
                # Stop service if it's running
                if self.service:
                    try:
                        self.service.stop()
                    except Exception as stop_error:
                        self.logger.error(f"Error stopping service: {stop_error}")
                    self.service = None
                
                if retry_count >= self.MAX_RETRIES:
                    self.logger.critical(
                        f"Max retries ({self.MAX_RETRIES}) reached, exiting"
                    )
                    sys.exit(1)
                
                # Exponential backoff (Requirement 2.6, 3.5)
                wait_time = min(
                    self.INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)),
                    self.MAX_RETRY_DELAY
                )
                self.logger.info(f"Restarting in {wait_time} seconds...")
                
                # Sleep in small increments to allow for graceful shutdown
                for _ in range(int(wait_time)):
                    if not self.running:
                        break
                    time.sleep(1)
        
        # Cleanup
        self.logger.info("Main loop exited, performing cleanup...")
        self.cleanup()
        
        self.logger.info("=" * 60)
        self.logger.info("Bato Scraping Service Container Stopped")
        self.logger.info("=" * 60)
    
    def shutdown(self, signum, frame):
        """
        Graceful shutdown handler.
        
        Requirements:
        - 8.1: Stop accepting new scraping jobs
        - 8.2: Wait for in-progress jobs (max 30 seconds)
        - 8.3: Close database connections cleanly
        - 8.4: Log shutdown completion
        - 8.5: Force-terminate if jobs still running after 30 seconds
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received signal {signal_name} ({signum}), initiating graceful shutdown...")
        
        self.running = False
        
        if self.service:
            try:
                # Requirement 8.1: Stop accepting new jobs
                self.logger.info("Stopping service (no new jobs will be accepted)...")
                self.service.stop()
                
                # Requirement 8.2: Wait for in-progress jobs
                self.logger.info(f"Waiting up to {self.SHUTDOWN_TIMEOUT} seconds for jobs to complete...")
                
                start_time = time.time()
                while time.time() - start_time < self.SHUTDOWN_TIMEOUT:
                    # Check if service thread has finished
                    if self.service.thread and self.service.thread.is_alive():
                        time.sleep(1)
                    else:
                        self.logger.info("All jobs completed successfully")
                        break
                else:
                    # Requirement 8.5: Force-terminate after timeout
                    if self.service.thread and self.service.thread.is_alive():
                        self.logger.warning(
                            f"Shutdown timeout ({self.SHUTDOWN_TIMEOUT}s) reached, "
                            "forcing termination"
                        )
                
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}", exc_info=True)
        
        # Requirement 8.4: Log shutdown completion
        self.logger.info("Graceful shutdown complete")
        
        sys.exit(0)
    
    def cleanup(self):
        """
        Cleanup resources before exit.
        
        Requirement 8.3: Close database connections cleanly
        """
        self.logger.info("Cleaning up resources...")
        
        # Stop service if still running
        if self.service:
            try:
                self.service.stop()
            except Exception as e:
                self.logger.error(f"Error stopping service during cleanup: {e}")
        
        # Close database connections (Requirement 8.3)
        try:
            # Dispose database handler (closes connection pool)
            if self.db_handler:
                self.db_handler.dispose()
                self.logger.info("Database connection handler disposed")
            
            # Also dispose global connections for compatibility
            db_session.remove()
            engine.dispose()
            
            self.logger.info("Database connections closed")
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
        
        self.logger.info("Cleanup complete")
    
    @staticmethod
    def main():
        """
        Entry point with argument parsing.
        
        Requirement 10.1-10.4: Support --test, --limit, --once flags
        """
        parser = argparse.ArgumentParser(
            description='Bato Scraping Service - Containerized Background Service'
        )
        
        # Requirement 10.1: --test flag
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run in test mode with detailed logging'
        )
        
        # Requirement 10.2: --limit flag
        parser.add_argument(
            '--limit',
            type=int,
            metavar='N',
            help='Limit number of manga to process (for testing)'
        )
        
        # Requirement 10.4: --once flag
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run a single scraping cycle then exit'
        )
        
        args = parser.parse_args()
        
        # Create and run service
        runner = BatoServiceRunner(
            test_mode=args.test,
            limit=args.limit,
            run_once=args.once
        )
        
        try:
            runner.run()
        except Exception as e:
            if runner.logger:
                runner.logger.critical(f"Fatal error: {e}", exc_info=True)
            else:
                print(f"Fatal error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    BatoServiceRunner.main()
