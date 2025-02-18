import asyncio
from datetime import datetime
import time
from typing import Callable

class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
        self.loop = None
        
    def _ensure_loop(self):
        """Ensure we have an event loop"""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
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
        self._ensure_loop()
        
        if not callback:
            callback = self._default_callback
            
        # Create and run the polling coroutine
        polling_coro = self.poll_notifications(notification_manager, interval, callback)
        self.tasks['notification_polling'] = self.loop.create_task(polling_coro)
        
    async def _default_callback(self, notifications):
        """Default callback just prints notifications"""
        for notification in notifications:
            print(f"New notification:\n{notification}")