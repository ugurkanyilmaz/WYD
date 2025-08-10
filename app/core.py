import os
from prometheus_client import Gauge, start_http_server

KAFKA_PRODUCER = None
KAFKA_CONSUMER = None
REDIS = None
MONGO = None

def init_metrics(port:int=8001):
    # Expose a separate metrics port (could integrate into main app using ASGI middleware)
    try:
        start_http_server(port)
    except Exception as e:
        print('prometheus start failed', e)

async def kafka_startup():
    """Start Kafka producer if dependencies are available; don't crash on failure."""
    global KAFKA_PRODUCER
    try:
        from aiokafka import AIOKafkaProducer
    except Exception as e:
        print('kafka import failed:', e)
        KAFKA_PRODUCER = None
        return
    try:
        brokers = os.getenv('KAFKA_BOOTSTRAP_SERVERS','localhost:9092')
        KAFKA_PRODUCER = AIOKafkaProducer(bootstrap_servers=brokers)
        await KAFKA_PRODUCER.start()
    except Exception as e:
        print('kafka startup failed:', e)
        KAFKA_PRODUCER = None

async def redis_startup():
    global REDIS
    try:
        import aioredis  # lazy import to avoid startup crash if incompatible
    except Exception as e:
        print('redis import failed:', e)
        REDIS = None
        return
    try:
        REDIS = await aioredis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0'), decode_responses=False)
    except Exception as e:
        print('redis startup failed:', e)
        REDIS = None

# S3 removed

async def mongo_startup():
    """Lightweight Mongo client for user settings and profiles."""
    global MONGO
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        MONGO = AsyncIOMotorClient(os.getenv('MONGO_URL','mongodb://localhost:27017'))
    except Exception as e:
        print('mongo startup failed:', e)
