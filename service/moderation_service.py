from dto.request import PredictRequest

class ModerationService:
    def __init__(self, moder_repo, redis_repo, item_repo):
        self.moder_repo = moder_repo
        self.redis_repo = redis_repo
        self.item_repo = item_repo

    def is_completed(self, result):
        if isinstance(result, dict):
            return result.get("status") == "completed"
        return getattr(result, "status", None) == "completed"

    async def get_prediction_for_item(self, item_id):
        cached = await self.redis_repo.get_moderation_for_item(item_id)
        if cached is not None and self.is_completed(cached):
            return cached
        result = await self.moder_repo.get_moderation_for_item(item_id)
        if result is not None and self.is_completed(result):
            return result
        return None

    async def get_moderation_task_id_for_item(self, item_id):
        item = await self.item_repo.get_item(item_id)
        if item is None:
            return None
        task = await self.moder_repo.create_moderation(item_id)
        await self.redis_repo.set_moderation(task.id, task)
        return task.id

    async def get_moderation_result(self, task_id):
        cached = await self.redis_repo.get_moderation(task_id)
        if cached is not None:
            status = cached.get("status") if isinstance(cached, dict) else getattr(cached, "status", None)
            if status not in (None, "pending"):
                return cached

        result = await self.moder_repo.get_moderation(task_id)
        if result is not None:
            await self.redis_repo.set_moderation(task_id, result)
        return result
    
    async def get_or_predict_for_item(self, item_id, model_service):
        cached = await self.get_prediction_for_item(item_id)
        if cached is not None:
            return cached
        result = await model_service.get_prediction_for_item(item_id)
        if result is not None:
            await self.save_prediction_to_cache(item_id, result)
        return result

    async def save_prediction_to_cache(self, item_id, result):
        if result is not None:
            if hasattr(result, 'id') and hasattr(result, 'item_id'):
                await self.redis_repo.set_moderation(result.id, result)
            else:
                await self.redis_repo.set_prediction_for_item(item_id, result)

    async def close_item(self, item_id):
        item = await self.item_repo.get_item(item_id)
        if item is None:
            return None
        task_ids = await self.moder_repo.delete_moderations_for_item(item_id)
        await self.redis_repo.delete_for_item(item_id, task_ids)
        closed = await self.item_repo.close_item(item_id)
        return closed
