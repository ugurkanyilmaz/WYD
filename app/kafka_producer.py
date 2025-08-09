from .core import KAFKA_PRODUCER
import json

async def publish(topic:str, data:dict):
    if not KAFKA_PRODUCER:
        raise RuntimeError('Kafka producer not started')
    await KAFKA_PRODUCER.send_and_wait(topic, json.dumps(data).encode('utf-8'))
