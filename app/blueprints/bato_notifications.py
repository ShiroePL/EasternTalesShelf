"""
Bato Notifications Blueprint
API endpoints for Bato.to notification system

Provides endpoints for:
- Fetching unread notifications
- Marking notifications as read
- Getting chapter lists
- Getting scraping schedules
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.database_module.bato_repository import BatoRepository
import logging

logger = logging.getLogger(__name__)

bato_notifications_bp = Blueprint('bato_notifications', __name__)


@bato_notifications_bp.route('/api/bato/notifications', methods=['GET'])
@login_required
def get_notifications():
    """
    Get unread notifications for the current user.
    
    Query Parameters:
        limit (int): Maximum number of notifications to return (default: 50)
    
    Returns:
        JSON response with notifications list
        
    Requirements: 8.1, 8.2
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Get unread notifications
        notifications = BatoRepository.get_unread_notifications(
            user_id=current_user.id,
            limit=limit
        )
        
        # Convert to JSON-serializable format
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,
                'anilist_id': notif.anilist_id,
                'bato_link': notif.bato_link,
                'notification_type': notif.notification_type,
                'manga_name': notif.manga_name,
                'message': notif.message,
                'chapter_dname': notif.chapter_dname,
                'chapter_full_url': notif.chapter_full_url,
                'old_status': notif.old_status,
                'new_status': notif.new_status,
                'chapters_count': notif.chapters_count,
                'importance': notif.importance,
                'is_read': notif.is_read,
                'is_emitted': notif.is_emitted,
                'created_at': notif.created_at.isoformat() if notif.created_at else None
            })
        
        # Get notification count
        count = BatoRepository.get_notification_count(user_id=current_user.id)
        
        return jsonify({
            'success': True,
            'notifications': notifications_data,
            'count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch notifications'
        }), 500


@bato_notifications_bp.route('/api/bato/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """
    Mark a notification as read.
    
    Args:
        notification_id (int): ID of the notification to mark as read
    
    Returns:
        JSON response with success status
        
    Requirements: 8.3
    """
    try:
        success = BatoRepository.mark_notification_read(notification_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Notification marked as read'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark notification as read'
        }), 500


@bato_notifications_bp.route('/api/bato/chapters/<int:anilist_id>', methods=['GET'])
@login_required
def get_manga_chapters(anilist_id):
    """
    Get chapter list for a manga.
    
    Args:
        anilist_id (int): AniList manga ID
    
    Query Parameters:
        limit (int): Maximum number of chapters to return (optional)
    
    Returns:
        JSON response with chapters list
        
    Requirements: 8.4
    """
    try:
        limit = request.args.get('limit', None, type=int)
        
        # Get chapters
        chapters = BatoRepository.get_chapters(anilist_id, limit=limit)
        
        # Convert to JSON-serializable format
        chapters_data = []
        for chapter in chapters:
            chapters_data.append({
                'id': chapter.id,
                'bato_chapter_id': chapter.bato_chapter_id,
                'chapter_number': chapter.chapter_number,
                'dname': chapter.dname,
                'title': chapter.title,
                'full_url': chapter.full_url,
                'date_public': chapter.date_public.isoformat() if chapter.date_public else None,
                'stat_count_views_total': chapter.stat_count_views_total,
                'is_read': chapter.is_read,
                'first_seen_at': chapter.first_seen_at.isoformat() if chapter.first_seen_at else None
            })
        
        return jsonify({
            'success': True,
            'anilist_id': anilist_id,
            'chapters': chapters_data,
            'count': len(chapters_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching chapters for anilist_id {anilist_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch chapters'
        }), 500


@bato_notifications_bp.route('/api/bato/schedule/<int:anilist_id>', methods=['GET'])
@login_required
def get_scraping_schedule(anilist_id):
    """
    Get scraping schedule information for a manga.
    
    Args:
        anilist_id (int): AniList manga ID
    
    Returns:
        JSON response with schedule information
        
    Requirements: 8.4
    """
    try:
        # Get schedule
        schedule = BatoRepository.get_schedule(anilist_id)
        
        if not schedule:
            return jsonify({
                'success': False,
                'error': 'Schedule not found for this manga'
            }), 404
        
        # Get manga details for additional context
        manga_details = BatoRepository.get_manga_details(anilist_id)
        
        schedule_data = {
            'anilist_id': schedule.anilist_id,
            'bato_link': schedule.bato_link,
            'scraping_interval_hours': schedule.scraping_interval_hours,
            'last_scraped_at': schedule.last_scraped_at.isoformat() if schedule.last_scraped_at else None,
            'next_scrape_at': schedule.next_scrape_at.isoformat() if schedule.next_scrape_at else None,
            'average_release_interval_days': schedule.average_release_interval_days,
            'preferred_release_day': schedule.preferred_release_day,
            'release_pattern_confidence': schedule.release_pattern_confidence,
            'total_chapters_tracked': schedule.total_chapters_tracked,
            'last_chapter_date': schedule.last_chapter_date.isoformat() if schedule.last_chapter_date else None,
            'consecutive_no_update_count': schedule.consecutive_no_update_count,
            'is_active': schedule.is_active,
            'priority': schedule.priority,
            'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
            'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None
        }
        
        # Add manga details if available
        if manga_details:
            schedule_data['manga_name'] = manga_details.name
            schedule_data['upload_status'] = manga_details.upload_status
        
        return jsonify({
            'success': True,
            'schedule': schedule_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching schedule for anilist_id {anilist_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch schedule'
        }), 500


@bato_notifications_bp.route('/api/bato/scrape/<int:anilist_id>', methods=['POST'])
@login_required
def trigger_manual_scrape(anilist_id):
    """
    Manually trigger a scraping job for a specific manga.
    This creates proper log entries that will show up in the admin panel.
    
    Args:
        anilist_id (int): AniList manga ID
    
    Returns:
        JSON response with scraping results
    """
    try:
        from app.services.bato.bato_scraping_service import get_service_instance
        from app.functions.class_mangalist import MangaList, db_session
        from datetime import datetime
        import re
        
        # Get manga from database
        manga = db_session.query(MangaList).filter(
            MangaList.id_anilist == anilist_id
        ).first()
        
        if not manga:
            return jsonify({
                'success': False,
                'error': 'Manga not found'
            }), 404
        
        if not manga.bato_link:
            return jsonify({
                'success': False,
                'error': 'Manga does not have a bato_link'
            }), 400
        
        # Extract bato_id
        match = re.search(r'/title/(\d+)', manga.bato_link)
        if not match:
            return jsonify({
                'success': False,
                'error': 'Invalid bato_link format'
            }), 400
        
        bato_id = match.group(1)
        
        # Prepare manga data for scraping service
        manga_data = {
            'anilist_id': manga.id_anilist,
            'bato_id': bato_id,
            'bato_link': manga.bato_link,
            'manga_name': manga.title_english or manga.title_romaji or 'Unknown'
        }
        
        # Get service instance and execute scraping job
        service = get_service_instance()
        success = service.execute_scraping_job(manga_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully scraped {manga_data["manga_name"]}',
                'anilist_id': anilist_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Scraping job failed. Check logs for details.'
            }), 500
        
    except Exception as e:
        logger.error(f"Error triggering manual scrape for {anilist_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to trigger scraping: {str(e)}'
        }), 500
