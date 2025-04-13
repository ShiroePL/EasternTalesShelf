from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.functions.class_mangalist import db_session, MangaList, MangaUpdatesDetails, MangaStatusNotification, AnilistNotification
from app.functions import sqlalchemy_fns
import logging
from sqlalchemy import text
from app.admin import admin_required
from functools import wraps

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/user/is-admin')
def is_user_admin():
    """Simple endpoint to check if current user is admin"""
    is_admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    return jsonify({'is_admin': is_admin})

@api_bp.route('/mangaupdates/<int:anilist_id>')
@login_required
def get_mangaupdates_info(anilist_id):
    # Get manga updates info from database
    try:
        manga_updates = db_session.query(MangaUpdatesDetails)\
            .filter(MangaUpdatesDetails.anilist_id == anilist_id)\
            .first()
        
        if manga_updates:
            return jsonify({
                'mangaupdates_status': manga_updates.status,
                'mangaupdates_licensed': manga_updates.licensed,
                'mangaupdates_completed': manga_updates.completed,
                'mangaupdates_last_updated': manga_updates.last_updated_timestamp
            })
        return jsonify({'error': 'No MangaUpdates info found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/notifications')
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

@api_bp.route('/notifications/<string:source>/<int:notification_id>/read', methods=['POST'])
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

@api_bp.route('/update_episodes', methods=['POST'])
@login_required
@admin_required
def update_episodes():
    """Update the number of episodes watched for an anime"""
    try:
        data = request.json
        anime_id = data.get('animeId')
        episodes = data.get('episodes')
        
        if not anime_id or episodes is None:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Validate that episodes is a number
        try:
            episodes = int(episodes)
            if episodes < 0:
                return jsonify({'success': False, 'message': 'Episodes must be a positive number'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Episodes must be a valid number'}), 400
            
        # Update the database using SQLAlchemy with text()
        try:
            db_session.execute(
                text("UPDATE anime_list SET episodes_progress = :episodes WHERE id_mal = :anime_id"),
                {"episodes": episodes, "anime_id": anime_id}
            )
            db_session.commit()
            
            # Log the successful update
            logging.info(f"Updated episodes for anime ID {anime_id} to {episodes}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully updated episodes to {episodes}'
            }), 200
            
        except Exception as db_error:
            db_session.rollback()
            logging.error(f"Database error during episode update: {db_error}")
            return jsonify({'success': False, 'message': f'Database error: {str(db_error)}'}), 500
            
    except Exception as e:
        logging.exception("Error updating episodes:")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/check_covers', methods=['POST'])
@login_required
def check_covers():
    """Check if the specified covers have been downloaded"""
    try:
        data = request.get_json()
        anilist_ids = data.get('anilist_ids', [])
        
        if not anilist_ids:
            logging.warning("Check covers called with no IDs")
            return jsonify({'error': 'No IDs provided'}), 400
        
        logging.info(f"Checking covers for {len(anilist_ids)} IDs")
        results = {}
        import os
        covers_dir = os.path.join('app', 'static', 'covers')
        
        # Ensure the covers directory exists
        if not os.path.exists(covers_dir):
            logging.warning(f"Covers directory does not exist: {covers_dir}")
            os.makedirs(covers_dir, exist_ok=True)
        
        for anilist_id in anilist_ids:
            # Check if AVIF exists first (preferred format)
            avif_path = os.path.join(covers_dir, f"{anilist_id}.avif")
            webp_path = os.path.join(covers_dir, f"{anilist_id}.webp")
            
            if os.path.exists(avif_path):
                logging.debug(f"Found AVIF cover for ID {anilist_id}")
                results[anilist_id] = {
                    'downloaded': True,
                    'format': 'avif',
                    'path': f'/static/covers/{anilist_id}.avif'
                }
            elif os.path.exists(webp_path):
                logging.debug(f"Found WebP cover for ID {anilist_id}")
                results[anilist_id] = {
                    'downloaded': True,
                    'format': 'webp', 
                    'path': f'/static/covers/{anilist_id}.webp'
                }
            else:
                logging.debug(f"No cover found for ID {anilist_id}")
                results[anilist_id] = {
                    'downloaded': False
                }
        
        # If any covers were found, update the database
        downloaded_ids = [int(id) for id, result in results.items() 
                         if result['downloaded'] and id.isdigit()]
        
        if downloaded_ids:
            logging.info(f"Updating database for {len(downloaded_ids)} newly found covers")
            try:
                sqlalchemy_fns.update_cover_download_status_bulk(downloaded_ids, True)
            except Exception as e:
                logging.error(f"Error updating cover status in database: {e}")
        
        return jsonify({'results': results})
    except Exception as e:
        logging.error(f"Error checking covers: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/notifications/read-all', methods=['POST'])
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

@api_bp.route('/notifications/count')
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

@api_bp.route('/manga/titles', methods=['POST'])
@login_required
def get_manga_titles():
    data = request.get_json()
    anilist_ids = data.get('anilist_ids', [])
    
    # Query the manga list table for titles
    titles = {}
    try:
        manga_entries = MangaList.query.filter(MangaList.id_anilist.in_(anilist_ids)).all()
        for entry in manga_entries:
            titles[entry.id_anilist] = entry.title_english
    except Exception as e:
        print(f"Error fetching manga titles: {e}")
        return jsonify({}), 500
        
    return jsonify(titles)

@api_bp.route('/notifications/refresh', methods=['POST'])
@login_required
@admin_required
def refresh_notifications():
    """Manual refresh endpoint"""
    from flask import current_app
    notifications = current_app.notification_manager.get_notifications()
    return jsonify(notifications) 