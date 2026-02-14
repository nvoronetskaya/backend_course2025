# app/clients/kafka.py
import json
from aiokafka import AIOKafkaProducer
from datetime import datetime, timezone

class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self._bootstrap = bootstrap_servers
        self._producer = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap)
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def send_json(self, topic: str, payload: dict) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started. Call await start() on startup.")
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._producer.send_and_wait(topic, data)

    async def send_moderation_request(self, item_id: int) -> None:
        payload = {
            "item_id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        await self.send_json("moderation", payload)
