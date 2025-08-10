import os
import asyncio
from prometheus_client import Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Global connection variables
KAFKA_PRODUCER = None
KAFKA_CONSUMER = None
REDIS = None
MONGO = None

# Connection ready flags
_redis_ready = False
_kafka_ready = False
_mongo_ready = False

async def get_redis():
    """Get Redis connection, initialize if not ready"""
    global REDIS, _redis_ready
    if not _redis_ready or REDIS is None:
        await redis_startup()
    return REDIS

async def get_kafka_producer():
    """Get Kafka producer, initialize if not ready"""
    global KAFKA_PRODUCER, _kafka_ready
    if not _kafka_ready or KAFKA_PRODUCER is None:
        await kafka_startup()
    return KAFKA_PRODUCER

async def get_mongo():
    """Get MongoDB client, initialize if not ready"""
    global MONGO, _mongo_ready
    if not _mongo_ready or MONGO is None:
        await mongo_startup()
    return MONGO

def init_metrics(port: int = 8001):
    """Initialize Prometheus metrics server"""
    try:
        start_http_server(port)
        logger.info("Prometheus metrics server started on port 8001")
    except Exception as e:
        logger.warning(f'Prometheus start failed: {e}')

async def kafka_startup():
    """Start Kafka producer with improved error handling and retries"""
    global KAFKA_PRODUCER, _kafka_ready
    
    try:
        from aiokafka import AIOKafkaProducer
        import ssl
    except ImportError as e:
        logger.warning(f'Kafka import failed: {e}')
        KAFKA_PRODUCER = None
        _kafka_ready = False
        return
    
    brokers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Kafka brokers: {brokers} (attempt {attempt + 1}/{max_retries})")
            
            KAFKA_PRODUCER = AIOKafkaProducer(
                bootstrap_servers=brokers,
                value_serializer=None,  # We'll handle serialization manually
                key_serializer=None,
                retry_backoff_ms=500,
                request_timeout_ms=30000,
                connections_max_idle_ms=300000,
                max_batch_size=32768,
                linger_ms=100,  # Allow batching for better throughput
                compression_type='gzip',  # Compress messages
                acks='all'  # Wait for all replicas
            )
            
            await KAFKA_PRODUCER.start()
            
            # Test the connection by sending a test message
            await KAFKA_PRODUCER.send('test-topic', b'connection-test')
            
            logger.info("Kafka producer connected successfully")
            _kafka_ready = True
            break
            
        except Exception as e:
            logger.warning(f'Kafka startup attempt {attempt + 1} failed: {e}')
            if KAFKA_PRODUCER:
                try:
                    await KAFKA_PRODUCER.stop()
                except Exception:
                    pass
                KAFKA_PRODUCER = None
            _kafka_ready = False
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying Kafka connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Failed to connect to Kafka after all retries")

async def redis_startup():
    """Start Redis connection with improved error handling and connection pooling"""
    global REDIS, _redis_ready
    
    try:
        from redis.asyncio import Redis
    except ImportError as e:
        logger.warning(f'Redis import failed: {e}')
        REDIS = None
        _redis_ready = False
        return
    
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    max_retries = 3
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Redis: {redis_url} (attempt {attempt + 1}/{max_retries})")
            
            REDIS = Redis.from_url(
                redis_url,
                decode_responses=False,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test the connection
            await REDIS.ping()
            
            logger.info("Redis connected successfully")
            _redis_ready = True
            break
            
        except Exception as e:
            logger.warning(f'Redis startup attempt {attempt + 1} failed: {e}')
            if REDIS:
                try:
                    await REDIS.close()
                except Exception:
                    pass
                REDIS = None
            _redis_ready = False
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying Redis connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Failed to connect to Redis after all retries")

async def mongo_startup():
    """Start MongoDB connection with improved error handling"""
    global MONGO, _mongo_ready
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError as e:
        logger.warning(f'MongoDB import failed: {e}')
        MONGO = None
        _mongo_ready = False
        return
    
    mongo_url = os.getenv('MONGO_URL', 'mongodb://mongo:27017')
    max_retries = 3
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to MongoDB: {mongo_url} (attempt {attempt + 1}/{max_retries})")
            
            MONGO = AsyncIOMotorClient(
                mongo_url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=5,
            )
            
            # Test the connection with a simple command
            server_info = await MONGO.admin.command('ping')
            
            logger.info(f"MongoDB connected successfully: {server_info}")
            _mongo_ready = True
            break
            
        except Exception as e:
            logger.warning(f'MongoDB startup attempt {attempt + 1} failed: {e}')
            if MONGO:
                try:
                    MONGO.close()
                except Exception:
                    pass
                MONGO = None
            _mongo_ready = False
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying MongoDB connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Failed to connect to MongoDB after all retries")

async def create_kafka_topics():
    """Create necessary Kafka topics for the application"""
    if not KAFKA_PRODUCER:
        logger.warning("Kafka producer not available, skipping topic creation")
        return
    
    topics = [
        "friend-requests-queue",
        "messages-queue", 
        "notifications-queue",
        "user-activity-queue",
        "media-processing-queue",
        "email-notifications-queue",
        "push-notifications-queue",
        "analytics-queue",
    ]
    
    try:
        from aiokafka.admin import AIOKafkaAdmin, NewTopic
        
        admin = AIOKafkaAdmin(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        )
        
        await admin.start()
        
        # Create topics with appropriate configuration for high throughput
        new_topics = []
        for topic in topics:
            new_topics.append(
                NewTopic(
                    name=topic,
                    num_partitions=8,  # Multiple partitions for scalability
                    replication_factor=1,  # Single replica for development
                    topic_configs={
                        'cleanup.policy': 'delete',
                        'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                        'segment.ms': str(24 * 60 * 60 * 1000),  # 1 day
                        'max.message.bytes': str(1024 * 1024),  # 1MB
                        'compression.type': 'gzip',
                    },
                )
            )
        
        await admin.create_topics(new_topics)
        logger.info(f"Created Kafka topics: {topics}")
        
    except Exception as e:
        logger.warning(f"Failed to create Kafka topics: {e}")
    finally:
        try:
            await admin.close()
        except Exception:
            pass

async def shutdown_connections():
    """Gracefully shutdown all connections"""
    logger.info("Shutting down connections...")
    
    if KAFKA_PRODUCER:
        try:
            await KAFKA_PRODUCER.stop()
            logger.info("Kafka producer stopped")
        except Exception as e:
            logger.error(f"Error stopping Kafka producer: {e}")
    
    if REDIS:
        try:
            await REDIS.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    if MONGO:
        try:
            MONGO.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
