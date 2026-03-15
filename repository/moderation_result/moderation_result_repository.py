import time
from sqlalchemy import select, delete
from datetime import datetime, timezone
from db.tables.moderation_result import ModerationResult
from app.metrics import DB_QUERY_DURATION

class ModerationResultRepository:
    def __init__(self, db, redis_repo=None):
        self.db = db
        self.redis_repo = redis_repo

    def is_completed(self, result):
        if isinstance(result, dict):
            return result.get("status") == "completed"
        return getattr(result, "status", None) == "completed"

    async def get_moderation(self, id):
        start = time.perf_counter()
        result = await self.db.execute(select(ModerationResult).where(ModerationResult.id == id).limit(1))
        DB_QUERY_DURATION.labels(query_type="select_moderation").observe(time.perf_counter() - start)
        return result.scalars().first()

    async def get_moderation_for_item(self, item_id):
        start = time.perf_counter()
        result = await self.db.execute(select(ModerationResult).where(ModerationResult.item_id == item_id).limit(1))
        DB_QUERY_DURATION.labels(query_type="select_moderation_by_item").observe(time.perf_counter() - start)
        return result.scalars().first()

    async def create_moderation(self, item_id):
        db_moderation = ModerationResult(
            item_id=item_id,
            status="pending",
            retry_count=0
        )
        self.db.add(db_moderation)
        start = time.perf_counter()
        await self.db.commit()
        DB_QUERY_DURATION.labels(query_type="insert_moderation").observe(time.perf_counter() - start)
        await self.db.refresh(db_moderation)
        return db_moderation
    
    async def get_latest_pending(self, db, item_id):
        res = await db.execute(
            select(ModerationResult)
            .where(ModerationResult.item_id == item_id, ModerationResult.status == "pending")
            .order_by(ModerationResult.id.desc())
            .limit(1)
        )
        return res.scalars().first()
    
    async def update_task(
        self,
        db,
        task_id,
        status,
        is_violation=None,
        probability=None,
        error_message=None,
        retry_count=None,
    ):
        obj = await db.get(ModerationResult, task_id)
        if obj is None:
            return
        obj.status = status
        obj.is_violation = is_violation
        obj.probability = probability
        obj.error_message = error_message
        if retry_count is not None:
            obj.retry_count = retry_count
        obj.processed_at = datetime.now(timezone.utc)
        await db.commit()
    
    async def increment_retry_count(self, db, task_id):
        obj = await db.get(ModerationResult, task_id)
        if obj is None:
            return None
        obj.retry_count += 1
        await db.commit()
        return obj.retry_count

    async def delete_moderations_for_item(self, item_id):
        result = await self.db.execute(
            select(ModerationResult.id).where(ModerationResult.item_id == item_id)
        )
        task_ids = [row[0] for row in result.all()]
        if task_ids:
            await self.db.execute(
                delete(ModerationResult).where(ModerationResult.item_id == item_id)
            )
            await self.db.commit()
        return task_ids

    async def get_completed_for_item(self, item_id):
        if self.redis_repo is not None:
            cached = await self.redis_repo.get_moderation_for_item(item_id)
            if cached is not None and self.is_completed(cached):
                return cached
        result = await self.get_moderation_for_item(item_id)
        if result is not None and self.is_completed(result):
            return result
        return None

    async def get_result(self, task_id):
        if self.redis_repo is not None:
            cached = await self.redis_repo.get_moderation(task_id)
            if cached is not None:
                status = cached.get("status") if isinstance(cached, dict) else getattr(cached, "status", None)
                if status not in (None, "pending"):
                    return cached

        result = await self.get_moderation(task_id)
        if result is not None and self.redis_repo is not None:
            await self.redis_repo.set_moderation(task_id, result)
        return result

    async def create_and_cache(self, item_id):
        task = await self.create_moderation(item_id)
        if self.redis_repo is not None:
            await self.redis_repo.set_moderation(task.id, task)
        return task

    async def save_to_cache(self, item_id, result):
        if result is None or self.redis_repo is None:
            return
        if hasattr(result, 'id') and hasattr(result, 'item_id'):
            await self.redis_repo.set_moderation(result.id, result)
        else:
            await self.redis_repo.set_prediction_for_item(item_id, result)

    async def delete_for_item(self, item_id):
        task_ids = await self.delete_moderations_for_item(item_id)
        if self.redis_repo is not None:
            await self.redis_repo.delete_for_item(item_id, task_ids)
        return task_ids
