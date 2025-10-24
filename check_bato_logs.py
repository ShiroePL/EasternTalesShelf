"""
Check Bato Scraper Logs

Quick script to check if scraper logs exist and show recent entries.

Usage:
    doppler run -- python check_bato_logs.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.functions.class_mangalist import db_session
from app.models.bato_models import (
    BatoScraperLog,
    BatoMangaDetails,
    BatoChapters,
    BatoScrapingSchedule
)
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_logs():
    """Check scraper logs and show statistics."""
    
    print("\n" + "="*60)
    print("BATO SCRAPER LOG CHECK")
    print("="*60)
    
    try:
        # Count records in each table
        log_count = db_session.query(BatoScraperLog).count()
        manga_count = db_session.query(BatoMangaDetails).count()
        chapter_count = db_session.query(BatoChapters).count()
        schedule_count = db_session.query(BatoScrapingSchedule).count()
        
        print(f"\n📊 Database Statistics:")
        print(f"  BatoScraperLog:        {log_count:>6} records")
        print(f"  BatoMangaDetails:      {manga_count:>6} records")
        print(f"  BatoChapters:          {chapter_count:>6} records")
        print(f"  BatoScrapingSchedule:  {schedule_count:>6} records")
        
        if log_count == 0:
            print("\n⚠️  WARNING: No scraper logs found!")
            print("   The admin panel will be empty.")
            print("\n💡 Solutions:")
            print("   1. Re-run: doppler run -- python app/migrations/populate_bato_initial_data.py")
            print("   2. Or run: doppler run -- python test_manual_scrape_with_logs.py")
            print("   3. Or wait for background service to run (every 5 minutes)")
        else:
            print(f"\n✓ Found {log_count} scraper log entries")
            
            # Show recent logs
            recent_logs = db_session.query(BatoScraperLog).order_by(
                BatoScraperLog.scraped_at.desc()
            ).limit(10).all()
            
            print(f"\n📋 Recent Scraping Jobs (last 10):")
            print("-" * 60)
            
            for log in recent_logs:
                status_icon = "✓" if log.status == "success" else "✗"
                print(f"{status_icon} {log.scraped_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  AniList ID: {log.anilist_id}")
                print(f"  Type: {log.scrape_type}, Status: {log.status}")
                print(f"  Chapters: {log.chapters_found} found, {log.new_chapters} new")
                print(f"  Duration: {log.duration_seconds:.2f}s")
                if log.error_message:
                    print(f"  Error: {log.error_message[:100]}")
                print()
            
            # Show statistics by type
            print("\n📈 Statistics by Scrape Type:")
            type_stats = db_session.query(
                BatoScraperLog.scrape_type,
                func.count(BatoScraperLog.id).label('count'),
                func.sum(BatoScraperLog.chapters_found).label('total_chapters'),
                func.sum(BatoScraperLog.new_chapters).label('total_new')
            ).group_by(BatoScraperLog.scrape_type).all()
            
            for stat in type_stats:
                print(f"  {stat.scrape_type:>10}: {stat.count:>4} jobs, "
                      f"{stat.total_chapters or 0:>5} chapters, "
                      f"{stat.total_new or 0:>5} new")
            
            # Show success rate
            print("\n📊 Success Rate:")
            success_count = db_session.query(BatoScraperLog).filter(
                BatoScraperLog.status == 'success'
            ).count()
            failed_count = db_session.query(BatoScraperLog).filter(
                BatoScraperLog.status == 'failed'
            ).count()
            
            total = success_count + failed_count
            if total > 0:
                success_rate = (success_count / total) * 100
                print(f"  Success: {success_count}/{total} ({success_rate:.1f}%)")
                print(f"  Failed:  {failed_count}/{total} ({100-success_rate:.1f}%)")
        
        print("\n" + "="*60)
        print("✓ Check complete")
        print("="*60)
        
        if log_count > 0:
            print("\n💡 View the admin panel at: http://localhost:5001/admin/bato")
        
    except Exception as e:
        logger.error(f"Error checking logs: {e}", exc_info=True)
    finally:
        db_session.remove()


if __name__ == '__main__':
    try:
        check_logs()
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Check failed: {e}", exc_info=True)
        sys.exit(1)
