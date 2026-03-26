"""
Migration: Add is_emitted column to bato_notifications table

This migration adds the is_emitted column to track which notifications
have been emitted via SocketIO to avoid duplicate emissions.

Requirements: 1.5
"""

import logging
from sqlalchemy import text
from app.functions.class_mangalist import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_is_emitted_column():
    """Add is_emitted column to bato_notifications table."""
    
    # Check database dialect
    dialect_name = engine.dialect.name
    logger.info(f"Database dialect: {dialect_name}")
    
    try:
        with engine.begin() as conn:  # Use begin() for automatic transaction management
            # Check if column already exists
            if dialect_name == 'sqlite':
                result = conn.execute(text(
                    "PRAGMA table_info(bato_notifications)"
                ))
                columns = [row[1] for row in result]
            else:  # MySQL/MariaDB
                result = conn.execute(text(
                    "SHOW COLUMNS FROM bato_notifications LIKE 'is_emitted'"
                ))
                columns = [row[0] for row in result]
            
            if 'is_emitted' in columns:
                logger.info("Column 'is_emitted' already exists in bato_notifications table")
                return
            
            # Add the column
            logger.info("Adding 'is_emitted' column to bato_notifications table...")
            
            if dialect_name == 'sqlite':
                # SQLite doesn't support adding columns with DEFAULT in ALTER TABLE
                # We need to add it without DEFAULT and then update
                conn.execute(text(
                    "ALTER TABLE bato_notifications ADD COLUMN is_emitted BOOLEAN"
                ))
                conn.execute(text(
                    "UPDATE bato_notifications SET is_emitted = 0 WHERE is_emitted IS NULL"
                ))
            else:  # MySQL/MariaDB
                conn.execute(text(
                    "ALTER TABLE bato_notifications ADD COLUMN is_emitted BOOLEAN DEFAULT FALSE NOT NULL"
                ))
            
            # Transaction is automatically committed when exiting the context manager
            logger.info("✅ Successfully added 'is_emitted' column to bato_notifications table")
            
    except Exception as e:
        logger.error(f"❌ Error adding is_emitted column: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    logger.info("Starting migration: Add is_emitted column to bato_notifications")
    add_is_emitted_column()
    logger.info("Migration completed successfully")
