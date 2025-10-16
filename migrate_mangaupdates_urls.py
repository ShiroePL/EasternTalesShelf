"""
One-time migration script to populate mangaupdates_url column
Run this script from the project root directory:
python migrate_mangaupdates_urls.py
"""
import logging
from app.functions.sqlalchemy_fns import migrate_mangaupdates_urls_from_external_links
from app.functions.class_mangalist import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_and_add_column():
    """Check if mangaupdates_url column exists, if not add it"""
    try:
        with engine.connect() as conn:
            # Try to query the column
            result = conn.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'mangaupdates_details' 
                AND COLUMN_NAME = 'mangaupdates_url'
            """))
            
            if result.fetchone() is None:
                logger.info("Column 'mangaupdates_url' does not exist, creating it...")
                conn.execute(text("""
                    ALTER TABLE mangaupdates_details 
                    ADD COLUMN mangaupdates_url VARCHAR(255)
                """))
                conn.commit()
                logger.info("Column 'mangaupdates_url' created successfully!")
            else:
                logger.info("Column 'mangaupdates_url' already exists")
                
    except Exception as e:
        logger.error(f"Error checking/adding column: {e}")
        raise

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Starting MangaUpdates URL Migration")
    logger.info("="*60)
    
    # Step 1: Ensure column exists
    logger.info("\nStep 1: Checking if mangaupdates_url column exists...")
    check_and_add_column()
    
    # Step 2: Run migration
    logger.info("\nStep 2: Migrating URLs from external_links...")
    result = migrate_mangaupdates_urls_from_external_links()
    
    # Step 3: Display results
    logger.info("\n" + "="*60)
    logger.info("Migration Results:")
    logger.info("="*60)
    
    if result["status"] == "success":
        logger.info(f"✓ Total MangaUpdates URLs found: {result['total_found']}")
        logger.info(f"✓ Existing entries updated: {result['total_updated']}")
        logger.info(f"✓ New entries created: {result['total_created']}")
        logger.info("\n✓ Migration completed successfully!")
    else:
        logger.error(f"✗ Migration failed: {result['message']}")
    
    logger.info("="*60)
