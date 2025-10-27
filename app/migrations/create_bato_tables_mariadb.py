"""
MIGRATION SCRIPT - INITIAL SETUP ONLY
This script was used for initial table creation and is kept for reference.
Tables are now managed through SQLAlchemy models in bato_models.py

Only run this if:
- Setting up a fresh database
- Recreating tables after a drop
- Deploying to a new environment

Current status: Tables already created and populated
"""

"""
Migration script to create Bato.to notification system tables in MariaDB

This script creates all required tables for the Bato notification system:
- bato_manga_details
- bato_chapters
- bato_notifications
- bato_scraper_log
- bato_scraping_schedule

Run this script once to initialize the database schema.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.functions.class_mangalist import engine
from app.models.bato_models import (
    Base,
    BatoMangaDetails,
    BatoChapters,
    BatoNotifications,
    BatoScraperLog,
    BatoScrapingSchedule
)
from sqlalchemy import inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_bato_tables():
    """Create all Bato tables in the database"""
    
    logger.info("Starting Bato tables migration...")
    logger.info(f"Database URI: {engine.url}")
    
    # Check if manga_list table exists (required for foreign keys)
    if not check_table_exists('manga_list'):
        logger.error("✗ Error: 'manga_list' table does not exist!")
        logger.error("The Bato tables require the manga_list table to exist first.")
        logger.error("Please ensure your main database tables are created.")
        raise Exception("Required table 'manga_list' not found")
    
    logger.info("✓ Required table 'manga_list' exists")
    
    bato_table_names = [
        'bato_manga_details',
        'bato_chapters',
        'bato_notifications',
        'bato_scraper_log',
        'bato_scraping_schedule'
    ]
    
    # Check which tables already exist
    existing_before = [t for t in bato_table_names if check_table_exists(t)]
    if existing_before:
        logger.info(f"Tables already exist: {', '.join(existing_before)}")
    
    # Create only Bato tables using Base.metadata.create_all
    # This will handle foreign key dependencies automatically
    try:
        logger.info("Creating Bato tables...")
        
        # Only create tables that are defined in bato_models
        # Filter to only Bato tables
        tables_to_create = [
            table for table in Base.metadata.sorted_tables
            if table.name in bato_table_names
        ]
        
        if tables_to_create:
            Base.metadata.create_all(engine, tables=tables_to_create, checkfirst=True)
            logger.info(f"✓ Table creation command executed")
        else:
            logger.warning("No Bato tables found in metadata")
        
        # Verify which tables were created
        created_count = 0
        skipped_count = 0
        
        for table_name in bato_table_names:
            if check_table_exists(table_name):
                if table_name in existing_before:
                    logger.info(f"✓ Table '{table_name}' already existed")
                    skipped_count += 1
                else:
                    logger.info(f"✓ Table '{table_name}' created successfully")
                    created_count += 1
            else:
                logger.error(f"✗ Table '{table_name}' was not created")
                
    except Exception as e:
        logger.error(f"✗ Error creating tables: {e}")
        raise
    
    logger.info("\n" + "="*60)
    logger.info(f"Migration completed!")
    logger.info(f"Tables created: {created_count}")
    logger.info(f"Tables skipped (already exist): {skipped_count}")
    logger.info("="*60)
    
    return created_count, skipped_count


if __name__ == '__main__':
    try:
        created, skipped = create_bato_tables()
        
        if created > 0:
            print(f"\n✓ Successfully created {created} new table(s)")
        if skipped > 0:
            print(f"✓ Skipped {skipped} existing table(s)")
            
        print("\nYou can now run the initial data population script:")
        print("  python app/migrations/populate_bato_initial_data.py")
        
    except Exception as e:
        logger.error(f"\n✗ Migration failed: {e}")
        sys.exit(1)
