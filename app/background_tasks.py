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

    async def poll_sync(self, interval: int):
        """
        Poll for sync with FastAPI at specified interval
        """
        from app.services.sync_service import perform_sync_with_fastapi
        while True:
            # Run the synchronous function in a separate thread to avoid blocking the event loop
            try:
                await self.loop.run_in_executor(None, perform_sync_with_fastapi)
            except Exception as e:
                print(f"Error in sync task: {e}")
            await asyncio.sleep(interval)

    def start_sync_task(self, interval: int = 900):
        """Start sync task"""
        self._ensure_loop()
        
        # Create and run the polling coroutine
        sync_coro = self.poll_sync(interval)
        self.tasks['sync_polling'] = self.loop.create_task(sync_coro)
