from datetime import timedelta
from app.clients.redis import get_redis_connection
from json import loads, dumps

class ModerationRedisRepository:
    def __init__(self):
        self._TTL = timedelta(minutes=30)
        self._TTL_SECONDS = int(self._TTL.total_seconds())
        self.task_prefix = 'task-'
        self.item_prefix = 'item-'

    def serialize(self, data):
        if hasattr(data, 'to_dict'):
            return dumps(data.to_dict())
        if hasattr(data, 'model_dump'):
            return dumps(data.model_dump())
        if isinstance(data, dict):
            return dumps(data)
        return dumps(data)

    async def get_moderation(self, id):
        async with get_redis_connection() as connection:
            row = await connection.get(f'{self.task_prefix}{id}')
            if row:
                return loads(row)
            return None
    
    async def get_moderation_for_item(self, item_id):
        async with get_redis_connection() as connection:
            row = await connection.get(f'{self.item_prefix}{item_id}')
            if row:
                return loads(row)
            return None
    
    async def set_moderation(self, id, data):
        async with get_redis_connection() as connection:
            task_id = f'{self.task_prefix}{id}'
            serialized = self.serialize(data)
            item_id_value = None
            if hasattr(data, 'item_id'):
                item_id_value = data.item_id
            elif isinstance(data, dict) and 'item_id' in data:
                item_id_value = data['item_id']

            pipeline = connection.pipeline()
            pipeline.set(name=task_id, value=serialized)
            pipeline.expire(task_id, self._TTL_SECONDS)
            if item_id_value is not None:
                item_key = f'{self.item_prefix}{item_id_value}'
                pipeline.set(name=item_key, value=serialized)
                pipeline.expire(item_key, self._TTL_SECONDS)
            await pipeline.execute()

    async def set_prediction_for_item(self, item_id, data):
        async with get_redis_connection() as connection:
            item_key = f'{self.item_prefix}{item_id}'
            serialized = self.serialize(data)
            await connection.set(item_key, serialized, ex=self._TTL_SECONDS)
    
    async def delete(self, id) -> None:
        async with get_redis_connection() as connection:
            await connection.delete(id)

    async def delete_for_item(self, item_id, task_ids) -> None:
        async with get_redis_connection() as connection:
            keys = [f'{self.item_prefix}{item_id}']
            keys.extend(f'{self.task_prefix}{tid}' for tid in task_ids)
            pipeline = connection.pipeline()
            for key in keys:
                pipeline.delete(key)
            await pipeline.execute()
