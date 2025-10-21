"""
NotificationManager - Creates and manages Bato.to chapter notifications

Handles creation of different notification types:
- Single chapter notifications
- Batch notifications (multiple chapters)
- Status change notifications (upload_status changes)

Integrates with SocketIO for real-time notifications.
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
from app.database_module.bato_repository import BatoRepository

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Creates and manages notifications for Bato manga updates.
    Emits real-time notifications via SocketIO.
    """
    
    def __init__(self):
        """Initialize the NotificationManager"""
        self.repository = BatoRepository()
    
    def create_new_chapter_notification(self, chapter_data: Dict) -> Optional[Dict]:
        """
        Create notification for a single new chapter.
        
        Args:
            chapter_data: Dictionary containing:
                - anilist_id: AniList manga ID
                - bato_link: Bato.to manga link
                - manga_name: Manga name for display
                - chapter_id: Database ID of the chapter
                - chapter_dname: Display name (e.g., "Chapter 112")
                - chapter_full_url: Full URL to the chapter
                
        Returns:
            Dictionary with notification data or None on error
        """
        try:
            # Validate required fields
            required_fields = ['anilist_id', 'bato_link', 'manga_name', 
                             'chapter_dname', 'chapter_full_url']
            for field in required_fields:
                if field not in chapter_data:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Create notification message
            message = f"New chapter available: {chapter_data['chapter_dname']}"
            
            # Prepare notification data
            notification_data = {
                'anilist_id': chapter_data['anilist_id'],
                'bato_link': chapter_data['bato_link'],
                'notification_type': 'new_chapter',
                'manga_name': chapter_data['manga_name'],
                'message': message,
                'chapter_id': chapter_data.get('chapter_id'),
                'chapter_dname': chapter_data['chapter_dname'],
                'chapter_full_url': chapter_data['chapter_full_url'],
                'chapters_count': 1,
                'importance': 1,  # Single chapter = importance 1
                'is_read': False
            }
            
            # Save to database
            notification = self.repository.create_notification(notification_data)
            
            if notification:
                logger.info(f"Created new chapter notification for {chapter_data['manga_name']}: {chapter_data['chapter_dname']}")
                
                # Emit WebSocket notification
                self.emit_websocket_notification({
                    'notification_id': notification.id,
                    'type': 'new_chapter',
                    'anilist_id': notification.anilist_id,
                    'manga_name': notification.manga_name,
                    'message': notification.message,
                    'chapter_url': notification.chapter_full_url,
                    'importance': notification.importance,
                    'created_at': notification.created_at.isoformat() if notification.created_at else None
                })
                
                return {
                    'notification_id': notification.id,
                    'type': 'new_chapter',
                    'message': message
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating new chapter notification: {e}")
            return None
    
    def create_batch_notification(self, manga_data: Dict, chapters: List[Dict]) -> Optional[Dict]:
        """
        Create notification for multiple new chapters (batch update).
        
        Args:
            manga_data: Dictionary containing:
                - anilist_id: AniList manga ID
                - bato_link: Bato.to manga link
                - manga_name: Manga name for display
            chapters: List of chapter dictionaries with chapter info
                
        Returns:
            Dictionary with notification data or None on error
        """
        try:
            # Validate required fields
            if not manga_data.get('anilist_id') or not manga_data.get('bato_link') or not manga_data.get('manga_name'):
                logger.error("Missing required manga data fields")
                return None
            
            if not chapters or len(chapters) == 0:
                logger.error("No chapters provided for batch notification")
                return None
            
            chapters_count = len(chapters)
            
            # Create notification message
            if chapters_count == 1:
                # If only one chapter, use single chapter notification instead
                return self.create_new_chapter_notification({
                    'anilist_id': manga_data['anilist_id'],
                    'bato_link': manga_data['bato_link'],
                    'manga_name': manga_data['manga_name'],
                    'chapter_id': chapters[0].get('chapter_id'),
                    'chapter_dname': chapters[0].get('chapter_dname', 'Unknown'),
                    'chapter_full_url': chapters[0].get('chapter_full_url', '')
                })
            
            # Get first and last chapter names for message
            first_chapter = chapters[0].get('chapter_dname', 'Unknown')
            last_chapter = chapters[-1].get('chapter_dname', 'Unknown')
            
            message = f"{chapters_count} new chapters available: {first_chapter} - {last_chapter}"
            
            # Use the URL of the first (newest) chapter
            chapter_url = chapters[0].get('chapter_full_url', '')
            
            # Prepare notification data
            notification_data = {
                'anilist_id': manga_data['anilist_id'],
                'bato_link': manga_data['bato_link'],
                'notification_type': 'batch_update',
                'manga_name': manga_data['manga_name'],
                'message': message,
                'chapter_id': chapters[0].get('chapter_id'),  # Link to first chapter
                'chapter_dname': first_chapter,
                'chapter_full_url': chapter_url,
                'chapters_count': chapters_count,
                'importance': 2,  # Batch update = importance 2
                'is_read': False
            }
            
            # Save to database
            notification = self.repository.create_notification(notification_data)
            
            if notification:
                logger.info(f"Created batch notification for {manga_data['manga_name']}: {chapters_count} chapters")
                
                # Emit WebSocket notification
                self.emit_websocket_notification({
                    'notification_id': notification.id,
                    'type': 'batch_update',
                    'anilist_id': notification.anilist_id,
                    'manga_name': notification.manga_name,
                    'message': notification.message,
                    'chapter_url': notification.chapter_full_url,
                    'chapters_count': chapters_count,
                    'importance': notification.importance,
                    'created_at': notification.created_at.isoformat() if notification.created_at else None
                })
                
                return {
                    'notification_id': notification.id,
                    'type': 'batch_update',
                    'message': message,
                    'chapters_count': chapters_count
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating batch notification: {e}")
            return None
    
    def create_status_change_notification(self, manga_data: Dict, old_status: str, new_status: str) -> Optional[Dict]:
        """
        Create notification for upload_status change (e.g., ongoing -> completed).
        
        Args:
            manga_data: Dictionary containing:
                - anilist_id: AniList manga ID
                - bato_link: Bato.to manga link
                - manga_name: Manga name for display
            old_status: Previous upload_status
            new_status: New upload_status
                
        Returns:
            Dictionary with notification data or None on error
        """
        try:
            # Validate required fields
            if not manga_data.get('anilist_id') or not manga_data.get('bato_link') or not manga_data.get('manga_name'):
                logger.error("Missing required manga data fields")
                return None
            
            if not old_status or not new_status:
                logger.error("Missing old_status or new_status")
                return None
            
            # Create notification message
            message = f"Status changed from '{old_status}' to '{new_status}'"
            
            # Prepare notification data
            notification_data = {
                'anilist_id': manga_data['anilist_id'],
                'bato_link': manga_data['bato_link'],
                'notification_type': 'status_change',
                'manga_name': manga_data['manga_name'],
                'message': message,
                'old_status': old_status,
                'new_status': new_status,
                'chapters_count': 0,
                'importance': 3,  # Status change = importance 3 (critical)
                'is_read': False
            }
            
            # Save to database
            notification = self.repository.create_notification(notification_data)
            
            if notification:
                logger.info(f"Created status change notification for {manga_data['manga_name']}: {old_status} -> {new_status}")
                
                # Emit WebSocket notification
                self.emit_websocket_notification({
                    'notification_id': notification.id,
                    'type': 'status_change',
                    'anilist_id': notification.anilist_id,
                    'manga_name': notification.manga_name,
                    'message': notification.message,
                    'old_status': old_status,
                    'new_status': new_status,
                    'importance': notification.importance,
                    'created_at': notification.created_at.isoformat() if notification.created_at else None
                })
                
                return {
                    'notification_id': notification.id,
                    'type': 'status_change',
                    'message': message,
                    'old_status': old_status,
                    'new_status': new_status
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating status change notification: {e}")
            return None
    
    def emit_websocket_notification(self, notification_data: Dict) -> bool:
        """
        Send real-time notification via SocketIO.
        
        Args:
            notification_data: Dictionary with notification info to emit
                
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular imports and to access current_app context
            from flask import current_app
            
            # Check if socketio is available
            if not hasattr(current_app, 'socketio'):
                logger.warning("SocketIO not available on current_app, skipping WebSocket emission")
                return False
            
            # Emit the notification event
            current_app.socketio.emit('bato_notification', notification_data)
            
            logger.debug(f"Emitted WebSocket notification: {notification_data.get('type')} for {notification_data.get('manga_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Error emitting WebSocket notification: {e}")
            return False
