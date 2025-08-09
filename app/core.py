import os
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import aioboto3
import aioredis
from prometheus_client import Gauge, start_http_server

KAFKA_PRODUCER = None
KAFKA_CONSUMER = None
REDIS = None
S3_SESSION = None

def init_metrics(port:int=8001):
    # Expose a separate metrics port (could integrate into main app using ASGI middleware)
    try:
        start_http_server(port)
    except Exception as e:
        print('prometheus start failed', e)

async def kafka_startup():
    global KAFKA_PRODUCER
    brokers = os.getenv('KAFKA_BOOTSTRAP_SERVERS','localhost:9092')
    KAFKA_PRODUCER = AIOKafkaProducer(bootstrap_servers=brokers)
    await KAFKA_PRODUCER.start()

async def redis_startup():
    global REDIS
    REDIS = await aioredis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0'), decode_responses=False)

async def init_s3():
    global S3_SESSION
    S3_SESSION = aioboto3.Session()
