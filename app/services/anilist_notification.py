import requests
import os
from datetime import datetime
import json
from typing import List, Dict, Any
from app.functions.class_mangalist import db_session, AnilistNotification


query = '''
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    notifications(resetNotificationCount: false) {
      ... on AiringNotification {
        id
        type
        animeId
        createdAt
        media { title { userPreferred } }
        episode
        contexts
      }
      ... on RelatedMediaAdditionNotification {
        id
        type
        mediaId
        createdAt
        media { title { userPreferred } }
        context
      }
      ... on MediaDataChangeNotification {
        id
        type
        mediaId
        createdAt
        media { title { userPreferred } }
        reason
        context
      }
      ... on MediaMergeNotification {
        id
        type
        createdAt
        mediaId
        deletedMediaTitles
        media { title { userPreferred } }
        reason
        context
      }
      ... on MediaDeletionNotification {
        id
        type
        createdAt
        deletedMediaTitle
        context
        reason
      }
    }
  }
}
'''

class AnilistNotificationManager:
    def __init__(self, user_token=None):
        # Try to use user's token if provided, otherwise fall back to app token
        self.user_token = user_token
        self.app_token = os.getenv('ANILIST_BEARER_TOKEN')
        
        if not self.user_token and not self.app_token:
            raise ValueError("Neither user token nor ANILIST_BEARER_TOKEN environment variable is set")
            
        self.last_notification_id = self._get_last_notification_id()
    
    def _get_last_notification_id(self) -> int:
        """Get the most recent notification ID from database"""
        latest = db_session.query(AnilistNotification)\
            .order_by(AnilistNotification.notification_id.desc())\
            .first()
        return latest.notification_id if latest else None

    def store_notifications(self, notifications: List[Dict[Any, Any]]) -> None:
        """Store new notifications in the database"""
        for notif in notifications:
            # Check if notification already exists
            existing = db_session.query(AnilistNotification)\
                .filter_by(notification_id=notif['id'])\
                .first()
            
            if existing:
                continue
                
            # Create new notification object
            new_notification = AnilistNotification(
                notification_id=notif['id'],
                type=notif['type'],
                created_at=datetime.fromtimestamp(notif['createdAt']),
                context=notif.get('context'),
                
                # Handle user info
                user_name=notif.get('user', {}).get('name') if 'user' in notif else None,
                
                # Handle media info
                media_title=notif.get('media', {}).get('title', {}).get('userPreferred') 
                    if 'media' in notif else None,
                media_id=notif.get('mediaId') or notif.get('animeId'),
                
                # Handle specific fields
                episode=notif.get('episode'),
                reason=notif.get('reason'),
                deleted_media_title=notif.get('deletedMediaTitle'),
                
                # Store any extra data as JSON
                extra_data={k: v for k, v in notif.items() 
                          if k not in ['id', 'type', 'createdAt', 'user', 'media', 
                                     'context', 'episode', 'reason', 'deletedMediaTitle']}
            )
            
            db_session.add(new_notification)
        
        try:
            db_session.commit()
        except Exception as e:
            print(f"Error storing notifications: {e}")
            db_session.rollback()

    def get_notifications(self, page: int = 1, per_page: int = 10) -> List[Dict[Any, Any]]:
        variables = {'page': page, 'perPage': per_page}
        
        # Use user token if available, otherwise use app token
        if self.user_token:
            headers = {'Authorization': f'Bearer {self.user_token}'}
            can_get_user_notifications = True
        else:
            headers = {'Authorization': f'Bearer {self.app_token}'}
            can_get_user_notifications = False
        
        try:
            # If we don't have a user token, we can't get user-specific notifications
            if not can_get_user_notifications:
                print("User token not available - cannot fetch personal notifications")
                return []
                
            response = requests.post(
                'https://graphql.anilist.co',
                json={'query': query, 'variables': variables},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            notifications = data['data']['Page']['notifications']
            valid_notifications = [n for n in notifications if n]
            
            # Store notifications in database
            self.store_notifications(valid_notifications)
            
            # Update last notification ID
            if valid_notifications:
                self.last_notification_id = valid_notifications[0]['id']
                
            return valid_notifications
            
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            if hasattr(e.response, 'json'):
                print("Error details:", e.response.json())
            return []

    def get_new_notifications(self) -> List[Dict[Any, Any]]:
        """Get only new notifications since last check"""
        # If we don't have a user token, we can't get user-specific notifications
        if not self.user_token:
            return []
            
        notifications = self.get_notifications(per_page=50)  # Get more to ensure we don't miss any
        if not notifications:
            return []
            
        if not self.last_notification_id:
            return notifications
            
        # Return only notifications that are newer than the last one we saw
        return [n for n in notifications if n['id'] > self.last_notification_id]

    def get_unread_notifications(self, limit: int = 10) -> List[AnilistNotification]:
        """Get unread notifications from database"""
        return db_session.query(AnilistNotification)\
            .filter_by(is_read=False)\
            .order_by(AnilistNotification.created_at.desc())\
            .limit(limit)\
            .all()

    def mark_as_read(self, notification_id: int) -> bool:
        """Mark a notification as read"""
        try:
            notification = db_session.query(AnilistNotification)\
                .filter_by(notification_id=notification_id)\
                .first()
            if notification:
                notification.is_read = True
                db_session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            db_session.rollback()
            return False

    def format_notification(self, notification: Dict[Any, Any]) -> str:
        """Format a notification into a readable string"""
        output = []
        output.append(f"Type: {notification['type']}")
        date = datetime.fromtimestamp(notification['createdAt'])
        output.append(f"Created: {date}")
        
        if 'media' in notification and 'title' in notification['media']:
            output.append(f"Media: {notification['media']['title']['userPreferred']}")
        if 'user' in notification:
            output.append(f"From user: {notification['user']['name']}")
        if 'reason' in notification:
            output.append(f"Reason: {notification['reason']}")
        if 'context' in notification:
            output.append(f"Context: {notification['context']}")
        if 'episode' in notification:
            output.append(f"Episode: {notification['episode']}")
        if 'deletedMediaTitle' in notification:
            output.append(f"Deleted Media: {notification['deletedMediaTitle']}")
            
        return "\n".join(output)
