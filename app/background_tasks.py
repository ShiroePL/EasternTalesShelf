import asyncio
from datetime import datetime
import time
from typing import Callable

class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
        
    async def poll_notifications(self, 
                               notification_manager, 
                               interval: int,
                               callback: Callable):
        """
        Poll for new notifications at specified interval
        
        Args:
            notification_manager: AnilistNotificationManager instance
            interval: Seconds between checks
            callback: Function to call with new notifications
        """
        while True:
            new_notifications = notification_manager.get_new_notifications()
            if new_notifications:
                await callback(new_notifications)
            await asyncio.sleep(interval)
            
    def start_polling(self, 
                     notification_manager, 
                     interval: int = 3600,  # 1 hour default
                     callback: Callable = None):
        """Start polling task"""
        if not callback:
            callback = self._default_callback
            
        task = asyncio.create_task(
            self.poll_notifications(notification_manager, interval, callback)
        )
        self.tasks['notification_polling'] = task
        
    async def _default_callback(self, notifications):
        """Default callback just prints notifications"""
        for notification in notifications:
            print(f"New notification:\n{notification}")