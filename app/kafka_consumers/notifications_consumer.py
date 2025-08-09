import asyncio
import os
import json
from aiokafka import AIOKafkaConsumer
from app.core import REDIS

async def run():
    brokers = os.getenv('KAFKA_BOOTSTRAP_SERVERS','localhost:9092')
    consumer = AIOKafkaConsumer('notifications', bootstrap_servers=brokers, group_id='notifications-worker')
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value)
            # persist or push via FCM/APNs (placeholder)
            print('got notification', data)
    finally:
        await consumer.stop()

if __name__ == '__main__':
    asyncio.run(run())
