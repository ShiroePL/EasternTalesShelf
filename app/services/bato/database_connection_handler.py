"""
Database Connection Handler for Bato Service

Provides robust database connection management for the standalone Bato service:
- Connection pooling configuration
- Retry logic with exponential backoff
- Connection verification
- "MySQL server has gone away" error handling
- Thread-safe connection management

Requirements:
- 3.1: Connect using same DATABASE_URI configuration
- 3.2: Use Doppler for secret management
- 3.4: Independent connection pooling
- 3.5: Retry logic with exponential backoff
- 5.3: Handle database errors gracefully
"""

import logging
import time
from typing import Optional, Callable, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import (
    OperationalError, 
    DatabaseError, 
    DisconnectionError,
    InterfaceError
)
from sqlalchemy.pool import QueuePool
from app.config import DATABASE_URI

logger = logging.getLogger(__name__)


class DatabaseConnectionHandler:
    """
    Manages database connections for the standalone Bato service.
    
    Features:
    - Connection pooling with pre-ping
    - Automatic reconnection on connection loss
    - Retry logic with exponential backoff
    - "MySQL server has gone away" error handling
    - Thread-safe session management
    """
    
    # Configuration constants
    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 1  # seconds
    MAX_RETRY_DELAY = 30  # seconds
    
    # Connection pool settings (Requirement 3.4)
    POOL_SIZE = 10  # Number of connections to maintain
    MAX_OVERFLOW = 5  # Additional connections when pool is full
    POOL_RECYCLE = 3600  # Recycle connections after 1 hour
    POOL_PRE_PING = True  # Test connections before using
    POOL_TIMEOUT = 30  # Timeout for getting connection from pool
    
    def __init__(self):
        """Initialize the database connection handler."""
        self.engine = None
        self.session_factory = None
        self.scoped_session = None
        self._initialized = False
        
        logger.info("DatabaseConnectionHandler initialized")
    
    def initialize(self) -> bool:
        """
        Initialize database engine and session factory.
        
        Requirements:
        - 3.1: Use DATABASE_URI configuration
        - 3.4: Configure connection pooling
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Initializing database connection...")
           
            
            # Create engine with connection pooling (Requirement 3.4)
            self.engine = create_engine(
                DATABASE_URI,
                poolclass=QueuePool,
                pool_size=self.POOL_SIZE,
                max_overflow=self.MAX_OVERFLOW,
                pool_recycle=self.POOL_RECYCLE,
                pool_pre_ping=self.POOL_PRE_PING,
                pool_timeout=self.POOL_TIMEOUT,
                echo=False,  # Set to True for SQL debugging
                connect_args={
                    'connect_timeout': 10  # Connection timeout in seconds
                }
            )
            
            # Add event listeners for connection management
            self._setup_event_listeners()
            
            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            # Create scoped session for thread-safe operations
            self.scoped_session = scoped_session(self.session_factory)
            
            self._initialized = True
            
            logger.info("Database connection initialized successfully")
            logger.info(
                f"Connection pool: size={self.POOL_SIZE}, "
                f"max_overflow={self.MAX_OVERFLOW}, "
                f"recycle={self.POOL_RECYCLE}s"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            self._initialized = False
            return False
    
    def _setup_event_listeners(self):
        """
        Set up SQLAlchemy event listeners for connection management.
        
        Handles:
        - Connection checkout (logging)
        - Connection errors (logging and cleanup)
        """
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Log when new connection is established."""
            logger.debug("New database connection established")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log when connection is checked out from pool."""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Log when connection is returned to pool."""
            logger.debug("Connection returned to pool")
    
    def verify_connection(self) -> bool:
        """
        Verify database connectivity with retry logic.
        
        Requirements:
        - 3.5: Retry logic with exponential backoff
        - 10.5: Verify database connectivity before starting
        
        Returns:
            True if connection is valid, False otherwise
        """
        if not self._initialized:
            logger.error("Database handler not initialized")
            return False
        
        retry_count = 0
        
        while retry_count < self.MAX_RETRIES:
            try:
                logger.info(
                    f"Verifying database connection "
                    f"(attempt {retry_count + 1}/{self.MAX_RETRIES})..."
                )
                
                # Try a simple query
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()
                
                logger.info("Database connection verified successfully")
                return True
                
            except (OperationalError, DatabaseError, DisconnectionError) as e:
                retry_count += 1
                error_msg = str(e).lower()
                
                logger.error(
                    f"Database connection verification failed "
                    f"(attempt {retry_count}/{self.MAX_RETRIES}): {e}"
                )
                
                if retry_count >= self.MAX_RETRIES:
                    logger.critical(
                        f"Failed to verify database connection after "
                        f"{self.MAX_RETRIES} attempts"
                    )
                    return False
                
                # Requirement 3.5: Exponential backoff
                delay = min(
                    self.INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)),
                    self.MAX_RETRY_DELAY
                )
                
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                logger.error(
                    f"Unexpected error verifying database connection: {e}",
                    exc_info=True
                )
                return False
        
        return False
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions with automatic cleanup.
        
        Handles:
        - Session creation
        - Automatic commit on success
        - Automatic rollback on error
        - Session cleanup
        - "MySQL server has gone away" errors
        
        Requirement 3.5: Handle "MySQL server has gone away" errors
        
        Usage:
            with handler.get_session() as session:
                session.query(Model).all()
        
        Yields:
            SQLAlchemy session
        """
        if not self._initialized:
            raise RuntimeError("Database handler not initialized")
        
        session = self.scoped_session()
        
        try:
            yield session
            session.commit()
            
        except (OperationalError, DisconnectionError, InterfaceError) as e:
            # Requirement 3.5: Handle "MySQL server has gone away"
            error_msg = str(e).lower()
            
            if any(phrase in error_msg for phrase in [
                'server has gone away',
                'lost connection',
                'connection was killed',
                'can\'t connect to',
                'connection refused'
            ]):
                logger.error(
                    f"Database connection lost: {e}. "
                    "Session will be rolled back and connection recycled."
                )
                session.rollback()
                
                # Dispose of the connection pool to force reconnection
                self.engine.dispose()
                logger.info("Connection pool disposed, will reconnect on next use")
            else:
                logger.error(f"Database operational error: {e}")
                session.rollback()
            
            raise
            
        except Exception as e:
            logger.error(f"Error in database session: {e}")
            session.rollback()
            raise
            
        finally:
            self.scoped_session.remove()
    
    def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute a database operation with retry logic.
        
        Requirements:
        - 3.5: Retry logic with exponential backoff
        - 5.3: Handle database errors gracefully
        
        Args:
            operation: Callable to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation
            
        Raises:
            Exception if all retries fail
        """
        retry_count = 0
        last_error = None
        
        while retry_count < self.MAX_RETRIES:
            try:
                return operation(*args, **kwargs)
                
            except (OperationalError, DisconnectionError, InterfaceError) as e:
                retry_count += 1
                last_error = e
                error_msg = str(e).lower()
                
                # Check if it's a connection error
                is_connection_error = any(phrase in error_msg for phrase in [
                    'server has gone away',
                    'lost connection',
                    'connection was killed',
                    'can\'t connect to',
                    'connection refused',
                    'deadlock'
                ])
                
                if is_connection_error:
                    logger.warning(
                        f"Database connection error in operation "
                        f"(attempt {retry_count}/{self.MAX_RETRIES}): {e}"
                    )
                    
                    # Dispose connection pool on connection errors
                    if 'server has gone away' in error_msg or 'lost connection' in error_msg:
                        self.engine.dispose()
                        logger.info("Connection pool disposed due to connection loss")
                    
                    if retry_count >= self.MAX_RETRIES:
                        logger.error(
                            f"Operation failed after {self.MAX_RETRIES} attempts"
                        )
                        raise
                    
                    # Requirement 3.5: Exponential backoff
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)),
                        self.MAX_RETRY_DELAY
                    )
                    
                    logger.info(f"Retrying operation in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Non-connection error, don't retry
                    logger.error(f"Database error (not retrying): {e}")
                    raise
                    
            except Exception as e:
                # Unexpected error, don't retry
                logger.error(f"Unexpected error in operation: {e}", exc_info=True)
                raise
        
        # All retries exhausted
        if last_error:
            raise last_error
    
    def dispose(self):
        """
        Dispose of database connections and cleanup resources.
        
        Requirement 8.3: Close database connections cleanly
        """
        if self.engine:
            try:
                logger.info("Disposing database connection pool...")
                
                # Remove scoped session
                if self.scoped_session:
                    self.scoped_session.remove()
                
                # Dispose engine (closes all connections)
                self.engine.dispose()
                
                logger.info("Database connections closed successfully")
                
            except Exception as e:
                logger.error(f"Error disposing database connections: {e}")
            
            finally:
                self.engine = None
                self.session_factory = None
                self.scoped_session = None
                self._initialized = False
    
    def get_pool_status(self) -> dict:
        """
        Get current connection pool status for monitoring.
        
        Returns:
            Dictionary with pool statistics
        """
        if not self.engine or not hasattr(self.engine.pool, 'size'):
            return {
                'initialized': False
            }
        
        pool = self.engine.pool
        
        return {
            'initialized': self._initialized,
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total_connections': pool.size() + pool.overflow()
        }
    
    @staticmethod
    def _mask_password(uri: str) -> str:
        """
        Mask password in database URI for logging.
        
        Args:
            uri: Database URI
            
        Returns:
            URI with masked password
        """
        try:
            if '://' in uri and '@' in uri:
                protocol, rest = uri.split('://', 1)
                if '@' in rest:
                    credentials, host = rest.split('@', 1)
                    if ':' in credentials:
                        user, _ = credentials.split(':', 1)
                        return f"{protocol}://{user}:****@{host}"
            return uri
        except Exception:
            return "****"


# Global instance for the Bato service
_db_handler: Optional[DatabaseConnectionHandler] = None


def get_db_handler() -> DatabaseConnectionHandler:
    """
    Get or create the global database handler instance.
    
    Returns:
        DatabaseConnectionHandler instance
    """
    global _db_handler
    
    if _db_handler is None:
        _db_handler = DatabaseConnectionHandler()
        _db_handler.initialize()
    
    return _db_handler


def initialize_db_handler() -> bool:
    """
    Initialize the global database handler.
    
    Returns:
        True if successful, False otherwise
    """
    global _db_handler
    
    _db_handler = DatabaseConnectionHandler()
    return _db_handler.initialize()


def dispose_db_handler():
    """Dispose of the global database handler."""
    global _db_handler
    
    if _db_handler:
        _db_handler.dispose()
        _db_handler = None
