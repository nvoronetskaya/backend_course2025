class ModerationService:
    def __init__(self, moder_repo, item_repo):
        self.moder_repo = moder_repo
        self.item_repo = item_repo

    async def get_prediction_for_item(self, item_id):
        return await self.moder_repo.get_completed_for_item(item_id)

    async def get_moderation_task_id_for_item(self, item_id):
        item = await self.item_repo.get_item(item_id)
        if item is None:
            return None
        task = await self.moder_repo.create_and_cache(item_id)
        return task.id

    async def get_moderation_result(self, task_id):
        return await self.moder_repo.get_result(task_id)

    async def get_or_predict_for_item(self, item_id, model_service):
        cached = await self.get_prediction_for_item(item_id)
        if cached is not None:
            return cached
        result = await model_service.get_prediction_for_item(item_id)
        if result is not None:
            await self.save_prediction_to_cache(item_id, result)
        return result

    async def save_prediction_to_cache(self, item_id, result):
        await self.moder_repo.save_to_cache(item_id, result)

    async def close_item(self, item_id):
        item = await self.item_repo.get_item(item_id)
        if item is None:
            return None
        await self.moder_repo.delete_for_item(item_id)
        closed = await self.item_repo.close_item(item_id)
        return closed
