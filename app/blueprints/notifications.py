from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.admin import admin_required
from app.functions.class_mangalist import db_session, MangaStatusNotification, AnilistNotification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('/')
@login_required
@admin_required
def get_notifications():
    """Get notifications from both MangaUpdates and AniList"""
    try:
        # Check if we should include read notifications
        include_read = request.args.get('include_read', 'false').lower() == 'true'
        
        # Get MangaUpdates notifications
        query_mu = db_session.query(MangaStatusNotification)
        if not include_read:
            query_mu = query_mu.filter(MangaStatusNotification.is_read == False)
        manga_notifications = query_mu.order_by(
            MangaStatusNotification.importance.desc(),
            MangaStatusNotification.created_at.desc()
        ).all()
        
        # Get AniList notifications
        query_al = db_session.query(AnilistNotification)
        if not include_read:
            query_al = query_al.filter(AnilistNotification.is_read == False)
        anilist_notifications = query_al.order_by(
            AnilistNotification.created_at.desc()
        ).all()
        
        # Get all manga entries for title mapping
        from app.functions.class_mangalist import MangaList
        manga_entries = db_session.query(MangaList).all()
        title_map = {
            entry.title_romaji: entry.title_english 
            for entry in manga_entries 
            if entry.title_english and entry.title_romaji
        }
        
        notifications = []
        
        # Format MangaUpdates notifications
        for n in manga_notifications:
            notifications.append({
                'id': n.id,
                'source': 'mangaupdates',
                'title': n.title,
                'type': n.notification_type,
                'message': n.message,
                'importance': n.importance,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'url': n.url,
                'anilist_id': n.anilist_id,
                'read': n.is_read  # Add read status to the response
            })
        
        # Format AniList notifications
        for n in anilist_notifications:
            # Try to get English title if available
            title = n.media_title
            if title in title_map:
                title = title_map[title]
            
            # Check if it's an anime notification by looking for animeId in extra_data
            is_anime = n.extra_data and 'animeId' in n.extra_data
            media_id = n.extra_data.get('animeId') if is_anime else n.media_id
            media_type = 'anime' if is_anime else 'manga'
            
            notifications.append({
                'id': n.notification_id,
                'source': 'anilist',
                'title': title,  # Use mapped title
                'original_title': n.media_title,  # Keep original title for reference
                'type': n.type,
                'message': n.reason or n.context or f"New {n.type.lower().replace('_', ' ')}",
                'importance': 1,
                'created_at': n.created_at.isoformat() if n.created_at else None,
                'url': f"https://anilist.co/{media_type}/{media_id}" if media_id else None,
                'anilist_id': n.media_id,
                'is_anime': is_anime,
                'read': n.is_read  # Add read status to the response
            })
        
        # Sort all notifications by creation date
        notifications.sort(key=lambda x: x['created_at'] if x['created_at'] else '', reverse=True)
        
        return jsonify({'notifications': notifications})
        
    except Exception as e:
        print(f"Error in get_notifications: {e}")
        return jsonify({'error': str(e), 'notifications': []}), 500

@notifications_bp.route('/<string:source>/<int:notification_id>/read', methods=['POST'])
@login_required
@admin_required
def mark_notification_read(source, notification_id):
    """Mark a notification as read"""
    try:
        if source == 'mangaupdates':
            notification = db_session.query(MangaStatusNotification)\
                .filter(MangaStatusNotification.id == notification_id)\
                .first()
            if notification:
                notification.is_read = True
                db_session.commit()
                return jsonify({'success': True})
        elif source == 'anilist':
            notification = db_session.query(AnilistNotification)\
                .filter(AnilistNotification.notification_id == notification_id)\
                .first()
            if notification:
                notification.is_read = True
                db_session.commit()
                return jsonify({'success': True})
        return jsonify({'error': 'Notification not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/read-all', methods=['POST'])
@login_required
@admin_required
def mark_all_notifications_read():
    try:
        # Mark all AniList notifications as read
        db_session.query(AnilistNotification)\
            .filter(AnilistNotification.is_read == False)\
            .update({AnilistNotification.is_read: True})
        
        # Mark all manga status notifications as read
        db_session.query(MangaStatusNotification)\
            .filter(MangaStatusNotification.is_read == False)\
            .update({MangaStatusNotification.is_read: True})
        
        # Commit the changes
        db_session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@notifications_bp.route('/count')
@login_required
@admin_required
def count_notifications():
    try:
        # Count unread AniList notifications
        anilist_count = db_session.query(AnilistNotification)\
            .filter(AnilistNotification.is_read == False)\
            .count()
        
        # Count unread manga status notifications
        manga_count = db_session.query(MangaStatusNotification)\
            .filter(MangaStatusNotification.is_read == False)\
            .count()
        
        # Calculate total count
        total_count = anilist_count + manga_count
        
        return jsonify({'count': total_count})
    except Exception as e:
        return jsonify({'count': 0, 'error': str(e)}), 500

@notifications_bp.route('/refresh', methods=['POST'])
@login_required
@admin_required
def refresh_notifications():
    """Manual refresh endpoint"""
    from flask import current_app
    notifications = current_app.notification_manager.get_notifications()
    return jsonify(notifications) 