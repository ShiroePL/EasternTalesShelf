"""
Bato Notification Polling Service

Polls the bato_notifications table for new notifications and emits them via SocketIO.
Runs as a background task in the main web application.

Requirements: 1.5
"""

import logging
import time
from threading import Thread, Event
from typing import Optional
from flask import current_app
from app.database_module.bato_repository import BatoRepository

logger = logging.getLogger(__name__)


class BatoNotificationPoller:
    """
    Background service that polls for new Bato notifications and emits them via SocketIO.
    
    This service bridges the gap between the standalone Bato scraping container
    and the web application's real-time notification system.
    """
    
    def __init__(self, socketio, poll_interval: int = 60):
        """
        Initialize the notification poller.
        
        Args:
            socketio: Flask-SocketIO instance for emitting notifications
            poll_interval: Seconds between polls (default: 60 = 1 minute)
        """
        self.socketio = socketio
        self.poll_interval = poll_interval
        self.running = False
        self.thread: Optional[Thread] = None
        self.stop_event = Event()
        
        logger.info(f"BatoNotificationPoller initialized with {poll_interval}s interval")
    
    def start(self):
        """Start the polling service in a background thread."""
        if self.running:
            logger.warning("BatoNotificationPoller is already running")
            return
        
        self.running = True
        self.stop_event.clear()
        self.thread = Thread(target=self._poll_loop, daemon=True, name="BatoNotificationPoller")
        self.thread.start()
        logger.info("BatoNotificationPoller started")
    
    def stop(self):
        """Stop the polling service gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping BatoNotificationPoller...")
        self.running = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("BatoNotificationPoller stopped")
    
    def _poll_loop(self):
        """Main polling loop that runs in background thread."""
        logger.info("BatoNotificationPoller poll loop started")
        
        while self.running and not self.stop_event.is_set():
            try:
                self._check_and_emit_notifications()
            except Exception as e:
                logger.error(f"Error in notification polling loop: {e}", exc_info=True)
            
            # Wait for next poll interval or stop event
            self.stop_event.wait(timeout=self.poll_interval)
        
        logger.info("BatoNotificationPoller poll loop ended")
    
    def _check_and_emit_notifications(self):
        """
        Check for new notifications and emit them via SocketIO.
        
        Requirements: 1.5
        """
        try:
            # Get unemitted notifications
            notifications = BatoRepository.get_unemitted_notifications(limit=100)
            
            if not notifications:
                logger.debug("No new notifications to emit")
                return
            
            logger.info(f"Found {len(notifications)} new Bato notifications to emit")
            
            # Emit each notification via SocketIO
            emitted_ids = []
            for notif in notifications:
                try:
                    notification_data = self._format_notification(notif)
                    
                    # Emit to all connected clients
                    self.socketio.emit(
                        'bato_notification',
                        notification_data,
                        namespace='/',
                        broadcast=True
                    )
                    
                    emitted_ids.append(notif.id)
                    logger.debug(
                        f"Emitted notification {notif.id}: "
                        f"{notif.notification_type} for {notif.manga_name}"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error emitting notification {notif.id}: {e}",
                        exc_info=True
                    )
            
            # Mark notifications as emitted
            if emitted_ids:
                success = BatoRepository.mark_notifications_emitted(emitted_ids)
                if success:
                    logger.info(f"Marked {len(emitted_ids)} notifications as emitted")
                else:
                    logger.error("Failed to mark notifications as emitted")
        
        except Exception as e:
            logger.error(f"Error checking and emitting notifications: {e}", exc_info=True)
    
    def _format_notification(self, notif) -> dict:
        """
        Format notification for SocketIO emission.
        
        Args:
            notif: BatoNotifications object
            
        Returns:
            Dictionary with notification data
        """
        return {
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
            'created_at': notif.created_at.isoformat() if notif.created_at else None,
            'source': 'bato'  # Identify this as a Bato notification
        }


# Global instance
_poller_instance: Optional[BatoNotificationPoller] = None


def init_bato_notification_poller(socketio, poll_interval: int = 60):
    """
    Initialize and start the Bato notification poller.
    
    Args:
        socketio: Flask-SocketIO instance
        poll_interval: Seconds between polls (default: 60)
        
    Returns:
        BatoNotificationPoller instance
    """
    global _poller_instance
    
    if _poller_instance is not None:
        logger.warning("BatoNotificationPoller already initialized")
        return _poller_instance
    
    _poller_instance = BatoNotificationPoller(socketio, poll_interval)
    _poller_instance.start()
    
    return _poller_instance


def get_poller_instance() -> Optional[BatoNotificationPoller]:
    """Get the global poller instance."""
    return _poller_instance


def stop_bato_notification_poller():
    """Stop the Bato notification poller."""
    global _poller_instance
    
    if _poller_instance is not None:
        _poller_instance.stop()
        _poller_instance = None
