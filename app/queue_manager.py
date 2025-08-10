"""
High-Performance Queue Management System
Handles different types of operations with separate queues for scalability
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from . import core
import logging

logger = logging.getLogger(__name__)

class QueueType(Enum):
    """Different queue types for different operations"""
    FRIEND_REQUESTS = "friend_requests"
    MESSAGES = "messages" 
    NOTIFICATIONS = "notifications"
    USER_ACTIVITY = "user_activity"
    MEDIA_PROCESSING = "media_processing"
    EMAIL_NOTIFICATIONS = "email_notifications"
    PUSH_NOTIFICATIONS = "push_notifications"
    ANALYTICS = "analytics"

class Priority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class QueueManager:
    """
    High-performance queue manager using Kafka for persistence and Redis for caching
    Supports +10,000 concurrent operations with horizontal scaling
    """
    
    def __init__(self):
        self.kafka_topics = {
            QueueType.FRIEND_REQUESTS: "friend-requests-queue",
            QueueType.MESSAGES: "messages-queue",
            QueueType.NOTIFICATIONS: "notifications-queue", 
            QueueType.USER_ACTIVITY: "user-activity-queue",
            QueueType.MEDIA_PROCESSING: "media-processing-queue",
            QueueType.EMAIL_NOTIFICATIONS: "email-notifications-queue",
            QueueType.PUSH_NOTIFICATIONS: "push-notifications-queue",
            QueueType.ANALYTICS: "analytics-queue"
        }
        
        self.redis_queues = {
            QueueType.FRIEND_REQUESTS: "queue:friend_requests",
            QueueType.MESSAGES: "queue:messages",
            QueueType.NOTIFICATIONS: "queue:notifications",
            QueueType.USER_ACTIVITY: "queue:user_activity",
            QueueType.MEDIA_PROCESSING: "queue:media_processing",
            QueueType.EMAIL_NOTIFICATIONS: "queue:email_notifications", 
            QueueType.PUSH_NOTIFICATIONS: "queue:push_notifications",
            QueueType.ANALYTICS: "queue:analytics"
        }

    async def enqueue(
        self, 
        queue_type: QueueType, 
        data: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        delay_seconds: int = 0,
        retry_count: int = 3,
        user_id: Optional[int] = None
    ) -> str:
        """
        Add job to queue with high performance
        Returns job_id for tracking
        """
        job_id = f"{queue_type.value}_{datetime.utcnow().timestamp()}_{hash(str(data)) % 10000}"
        
        job_data = {
            "id": job_id,
            "type": queue_type.value,
            "data": data,
            "priority": priority.value,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": retry_count,
            "user_id": user_id,
            "status": "pending"
        }

        try:
            # High priority jobs go to Redis for immediate processing
            if priority in [Priority.HIGH, Priority.CRITICAL]:
                await self._enqueue_redis(queue_type, job_data, priority)
            
            # All jobs also go to Kafka for persistence and horizontal scaling
            await self._enqueue_kafka(queue_type, job_data)
            
            # Track job for monitoring
            await self._track_job(job_id, job_data)
            
            logger.info(f"Job {job_id} enqueued to {queue_type.value}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {job_id}: {str(e)}")
            raise

    async def _enqueue_redis(self, queue_type: QueueType, job_data: Dict, priority: Priority):
        """Enqueue to Redis for fast processing"""
        redis_client = await core.get_redis()
        if not redis_client:
            return

        queue_name = self.redis_queues[queue_type]

        # Use priority queues in Redis
        if priority == Priority.CRITICAL:
            queue_name += ":critical"
        elif priority == Priority.HIGH:
            queue_name += ":high"
        else:
            queue_name += ":normal"

        await redis_client.lpush(queue_name, json.dumps(job_data))

        # Set expiration for job data (24 hours)
        await redis_client.expire(queue_name, 86400)

    async def _enqueue_kafka(self, queue_type: QueueType, job_data: Dict):
        """Enqueue to Kafka for persistence and scaling"""
        kafka_producer = await core.get_kafka_producer()
        if not kafka_producer:
            return

        topic = self.kafka_topics[queue_type]

        # Partition by user_id for better distribution
        partition_key = str(job_data.get('user_id', 0)).encode()

        await kafka_producer.send(
            topic,
            value=json.dumps(job_data).encode('utf-8'),
            key=partition_key
        )

    async def _track_job(self, job_id: str, job_data: Dict):
        """Track job status in Redis"""
        redis_client = await core.get_redis()
        if not redis_client:
            return

        await redis_client.setex(f"job:{job_id}", 3600, json.dumps(job_data))  # 1 hour TTL

    async def dequeue(self, queue_type: QueueType, batch_size: int = 1) -> List[Dict]:
        """
        Dequeue jobs for processing with batch support for high throughput
        """
        jobs = []

        redis_client = await core.get_redis()
        if not redis_client:
            return jobs

        queue_name = self.redis_queues[queue_type]

        # Process critical and high priority first
        for priority_suffix in [":critical", ":high", ":normal"]:
            priority_queue = queue_name + priority_suffix
            
            for _ in range(batch_size):
                job_data = await redis_client.rpop(priority_queue)
                if job_data:
                    try:
                        if isinstance(job_data, (bytes, bytearray)):
                            job = json.loads(job_data.decode("utf-8"))
                        else:
                            job = json.loads(job_data)
                        jobs.append(job)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid job data in queue: {job_data}")
                        
                if len(jobs) >= batch_size:
                    break
                    
            if len(jobs) >= batch_size:
                break
                
        return jobs

    async def get_queue_stats(self) -> Dict[str, Dict[str, int]]:
        """Get queue statistics for monitoring"""
        stats = {}

        redis_client = await core.get_redis()
        if not redis_client:
            return stats

        for queue_type, redis_queue in self.redis_queues.items():
            queue_stats = {
                "critical": 0,
                "high": 0, 
                "normal": 0,
                "total": 0
            }
            
            for priority in ["critical", "high", "normal"]:
                queue_name = f"{redis_queue}:{priority}"
                try:
                    length = await redis_client.llen(queue_name)
                    queue_stats[priority] = length
                    queue_stats["total"] += length
                except:
                    queue_stats[priority] = 0
                    
            stats[queue_type.value] = queue_stats
            
        return stats

    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status by ID"""
        redis_client = await core.get_redis()
        if not redis_client:
            return None

        job_data = await redis_client.get(f"job:{job_id}")
        if job_data:
            try:
                if isinstance(job_data, (bytes, bytearray)):
                    return json.loads(job_data.decode("utf-8"))
                return json.loads(job_data)
            except json.JSONDecodeError:
                logger.error(f"Invalid job status data for job {job_id}: {job_data}")
                return None
        return None

    async def update_job_status(self, job_id: str, status: str, result: Optional[Dict] = None):
        """Update job status"""
        redis_client = await core.get_redis()
        if not redis_client:
            return

        job_data = await self.get_job_status(job_id)
        if job_data:
            job_data["status"] = status
            job_data["updated_at"] = datetime.utcnow().isoformat()
            if result:
                job_data["result"] = result
                
            await redis_client.setex(f"job:{job_id}", 3600, json.dumps(job_data))

    async def initialize(self):
        """Initialize the queue manager"""
        logger.info("Initializing Queue Manager...")
        try:
            # Wait a moment for core services to be ready
            import time
            await asyncio.sleep(0.5)
            
            # Test Redis connection
            redis_client = await core.get_redis()
            if redis_client:
                await redis_client.ping()
                logger.info("Queue Manager initialized with Redis")
            else:
                logger.warning("Queue Manager initialized without Redis")
                
            # Test Kafka connection
            kafka_producer = await core.get_kafka_producer()
            if kafka_producer:
                logger.info("Queue Manager initialized with Kafka")
            else:
                logger.warning("Queue Manager initialized without Kafka")
                
            # Test MongoDB connection
            mongo_client = await core.get_mongo()
            if mongo_client:
                await mongo_client.admin.command('ping')
                logger.info("Queue Manager initialized with MongoDB")
            else:
                logger.warning("Queue Manager initialized without MongoDB")
                
        except Exception as e:
            logger.error(f"Queue Manager initialization failed: {e}")
            raise

    async def close(self):
        """Close the queue manager"""
        logger.info("Closing Queue Manager...")
        try:
            # Clean up any resources if needed
            logger.info("Queue Manager closed successfully")
        except Exception as e:
            logger.error(f"Queue Manager close failed: {e}")

# Global queue manager instance
queue_manager = QueueManager()

# Convenience functions for different operations
async def enqueue_friend_request(from_user_id: int, to_user_id: int, action: str):
    """Queue friend request processing"""
    return await queue_manager.enqueue(
        QueueType.FRIEND_REQUESTS,
        {
            "from_user_id": from_user_id,
            "to_user_id": to_user_id, 
            "action": action
        },
        priority=Priority.HIGH,
        user_id=from_user_id
    )

async def enqueue_message(sender_id: int, recipient_id: int, content: str, message_id: int):
    """Queue message processing"""
    return await queue_manager.enqueue(
        QueueType.MESSAGES,
        {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "content": content,
            "message_id": message_id
        },
        priority=Priority.HIGH,
        user_id=sender_id
    )

async def enqueue_notification(user_id: int, title: str, body: str, notification_type: str):
    """Queue notification processing"""
    return await queue_manager.enqueue(
        QueueType.NOTIFICATIONS,
        {
            "user_id": user_id,
            "title": title,
            "body": body,
            "type": notification_type
        },
        priority=Priority.NORMAL,
        user_id=user_id
    )

async def enqueue_user_activity(user_id: int, activity_type: str, data: Dict):
    """Queue user activity logging"""
    return await queue_manager.enqueue(
        QueueType.USER_ACTIVITY,
        {
            "user_id": user_id,
            "activity_type": activity_type,
            "data": data
        },
        priority=Priority.LOW,
        user_id=user_id
    )

async def enqueue_analytics_event(event_type: str, data: Dict, user_id: Optional[int] = None):
    """Queue analytics event"""
    return await queue_manager.enqueue(
        QueueType.ANALYTICS,
        {
            "event_type": event_type,
            "data": data,
            "user_id": user_id
        },
        priority=Priority.LOW,
        user_id=user_id
    )
