"""
High-Performance Queue Workers
Processes different types of queued operations for scalability
"""
import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from .queue_manager import queue_manager, QueueType
from .cache import cache
from .crud import create_notification, create_friendship, get_user, get_message
from .kafka_producer import publish

logger = logging.getLogger(__name__)

class BaseWorker:
    """Base worker class for processing queue jobs"""
    
    def __init__(self, queue_type: QueueType, batch_size: int = 10, delay: float = 1.0):
        self.queue_type = queue_type
        self.batch_size = batch_size
        self.delay = delay
        self.running = False
        self.processed_count = 0
        self.error_count = 0
    
    async def start(self):
        """Start the worker"""
        self.running = True
        logger.info(f"Starting {self.__class__.__name__} for queue {self.queue_type.value}")
        
        while self.running:
            try:
                jobs = await queue_manager.dequeue(self.queue_type, self.batch_size)
                
                if not jobs:
                    await asyncio.sleep(self.delay)
                    continue
                
                # Process jobs in parallel for better throughput
                tasks = [self.process_job(job) for job in jobs]
                await asyncio.gather(*tasks, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"Worker {self.__class__.__name__} error: {str(e)}")
                self.error_count += 1
                await asyncio.sleep(self.delay)
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info(f"Stopping {self.__class__.__name__}")
    
    async def process_job(self, job: Dict[str, Any]):
        """Process individual job - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def mark_job_completed(self, job_id: str, result: Dict = None):
        """Mark job as completed"""
        await queue_manager.update_job_status(job_id, "completed", result)
        self.processed_count += 1
    
    async def mark_job_failed(self, job_id: str, error: str):
        """Mark job as failed"""
        await queue_manager.update_job_status(job_id, "failed", {"error": error})
        self.error_count += 1

class FriendRequestWorker(BaseWorker):
    """Worker for processing friend requests"""
    
    def __init__(self):
        super().__init__(QueueType.FRIEND_REQUESTS, batch_size=20, delay=0.5)
    
    async def process_job(self, job: Dict[str, Any]):
        """Process friend request job"""
        job_id = job["id"]
        data = job["data"]
        
        try:
            from_user_id = data["from_user_id"]
            to_user_id = data["to_user_id"]
            action = data["action"]
            
            if action == "send_request":
                # Create notification for friend request
                from_user = await get_user(from_user_id)
                if from_user:
                    await create_notification(
                        to_user_id,
                        f"Friend request from {from_user.display_name or from_user.username}"
                    )
                    
                    # Invalidate user's friend request cache
                    await cache.delete(f"friend_requests:{to_user_id}")
                    
                    # Analytics event
                    await publish("analytics-queue", {
                        "event": "friend_request_sent",
                        "from_user_id": from_user_id,
                        "to_user_id": to_user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif action == "accept_request":
                # Create friendship
                await create_friendship(from_user_id, to_user_id)
                
                # Create notification for acceptance
                to_user = await get_user(to_user_id)
                if to_user:
                    await create_notification(
                        from_user_id,
                        f"{to_user.display_name or to_user.username} accepted your friend request"
                    )
                
                # Invalidate friends cache for both users
                await cache.delete(f"friends:{from_user_id}")
                await cache.delete(f"friends:{to_user_id}")
                
                # Analytics event
                await publish("analytics-queue", {
                    "event": "friend_request_accepted",
                    "from_user_id": from_user_id,
                    "to_user_id": to_user_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            await self.mark_job_completed(job_id)
            logger.debug(f"Friend request job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process friend request job {job_id}: {str(e)}")
            await self.mark_job_failed(job_id, str(e))

class MessageWorker(BaseWorker):
    """Worker for processing messages"""
    
    def __init__(self):
        super().__init__(QueueType.MESSAGES, batch_size=50, delay=0.2)
    
    async def process_job(self, job: Dict[str, Any]):
        """Process message job"""
        job_id = job["id"]
        data = job["data"]
        
        try:
            sender_id = data["sender_id"]
            recipient_id = data["recipient_id"]
            content = data["content"]
            message_id = data["message_id"]
            
            # Create notification for new message
            sender = await get_user(sender_id)
            if sender:
                await create_notification(
                    recipient_id,
                    f"New message from {sender.display_name or sender.username}",
                    notification_type="message"
                )
            
            # Invalidate conversation cache
            await cache.delete(f"conv:{min(sender_id, recipient_id)}:{max(sender_id, recipient_id)}")
            
            # Update user activity
            await publish("user-activity-queue", {
                "user_id": sender_id,
                "activity": "sent_message",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"recipient_id": recipient_id, "message_id": message_id}
            })
            
            # Analytics event
            await publish("analytics-queue", {
                "event": "message_sent",
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message_length": len(content)
            })
            
            await self.mark_job_completed(job_id)
            logger.debug(f"Message job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process message job {job_id}: {str(e)}")
            await self.mark_job_failed(job_id, str(e))

class NotificationWorker(BaseWorker):
    """Worker for processing notifications"""
    
    def __init__(self):
        super().__init__(QueueType.NOTIFICATIONS, batch_size=100, delay=0.1)
    
    async def process_job(self, job: Dict[str, Any]):
        """Process notification job"""
        job_id = job["id"]
        data = job["data"]
        
        try:
            user_id = data["user_id"]
            title = data["title"]
            body = data["body"]
            notification_type = data.get("type", "general")
            
            # Store notification in cache for real-time access
            notification_data = {
                "title": title,
                "body": body,
                "type": notification_type,
                "timestamp": datetime.utcnow().isoformat(),
                "read": False
            }
            
            # Add to user's notification list in cache
            notifications = await cache.get_list(f"notifications:{user_id}")
            notifications.insert(0, notification_data)  # Add to beginning
            
            # Keep only last 100 notifications
            if len(notifications) > 100:
                notifications = notifications[:100]
            
            await cache.set_list(f"notifications:{user_id}", notifications, ttl=86400)  # 24 hours
            
            # Send push notification (queue for push notification worker)
            await queue_manager.enqueue(
                QueueType.PUSH_NOTIFICATIONS,
                {
                    "user_id": user_id,
                    "title": title,
                    "body": body,
                    "type": notification_type
                },
                user_id=user_id
            )
            
            await self.mark_job_completed(job_id)
            logger.debug(f"Notification job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process notification job {job_id}: {str(e)}")
            await self.mark_job_failed(job_id, str(e))

class UserActivityWorker(BaseWorker):
    """Worker for processing user activity logs"""
    
    def __init__(self):
        super().__init__(QueueType.USER_ACTIVITY, batch_size=200, delay=1.0)
    
    async def process_job(self, job: Dict[str, Any]):
        """Process user activity job"""
        job_id = job["id"]
        data = job["data"]
        
        try:
            user_id = data["user_id"]
            activity_type = data["activity_type"]
            activity_data = data["data"]
            
            # Store in MongoDB for analytics
            from .core import MONGO
            if MONGO:
                activity_doc = {
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "data": activity_data,
                    "timestamp": datetime.utcnow()
                }
                
                await MONGO.social_app.user_activities.insert_one(activity_doc)
            
            # Update user's last activity in cache
            await cache.set(f"last_activity:{user_id}", datetime.utcnow().isoformat(), ttl=86400)
            
            await self.mark_job_completed(job_id)
            logger.debug(f"User activity job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process user activity job {job_id}: {str(e)}")
            await self.mark_job_failed(job_id, str(e))

class AnalyticsWorker(BaseWorker):
    """Worker for processing analytics events"""
    
    def __init__(self):
        super().__init__(QueueType.ANALYTICS, batch_size=500, delay=2.0)
    
    async def process_job(self, job: Dict[str, Any]):
        """Process analytics job"""
        job_id = job["id"]
        data = job["data"]
        
        try:
            event_type = data["event_type"]
            event_data = data["data"]
            user_id = data.get("user_id")
            
            # Store in MongoDB for analytics
            from .core import MONGO
            if MONGO:
                analytics_doc = {
                    "event_type": event_type,
                    "data": event_data,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow()
                }
                
                await MONGO.social_app.analytics_events.insert_one(analytics_doc)
            
            # Update real-time metrics in Redis
            today = datetime.utcnow().strftime("%Y-%m-%d")
            hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
            
            await cache.increment(f"metrics:daily:{event_type}:{today}", 1)
            await cache.increment(f"metrics:hourly:{event_type}:{hour}", 1)
            
            if user_id:
                await cache.increment(f"metrics:user:{event_type}:{user_id}", 1)
            
            await self.mark_job_completed(job_id)
            logger.debug(f"Analytics job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process analytics job {job_id}: {str(e)}")
            await self.mark_job_failed(job_id, str(e))

# Worker manager
class WorkerManager:
    """Manages all workers"""
    
    def __init__(self):
        self.workers = [
            FriendRequestWorker(),
            MessageWorker(),
            NotificationWorker(),
            UserActivityWorker(),
            AnalyticsWorker()
        ]
        self.tasks = []
    
    async def start_all(self):
        """Start all workers"""
        logger.info("Starting all queue workers...")
        
        for worker in self.workers:
            task = asyncio.create_task(worker.start())
            self.tasks.append(task)
        
        logger.info(f"Started {len(self.workers)} queue workers")
    
    async def stop_all(self):
        """Stop all workers"""
        logger.info("Stopping all queue workers...")
        
        # Stop all workers
        for worker in self.workers:
            await worker.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All queue workers stopped")
    
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get worker statistics"""
        stats = {}
        for worker in self.workers:
            stats[worker.queue_type.value] = {
                "processed": worker.processed_count,
                "errors": worker.error_count,
                "running": worker.running
            }
        return stats

# Global worker manager
worker_manager = WorkerManager()
