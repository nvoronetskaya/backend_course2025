import time
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import text
from app.metrics import DB_QUERY_DURATION

class ModerationResultRepository:
    def __init__(self, db, redis_repo=None):
        self.db = db
        self.redis_repo = redis_repo
    
    def to_bool(self, val):
        if isinstance(val, str):
            return val.lower() != "false"
        return bool(val)

    def to_obj(self, row):
        if row is None:
            return None
        d = dict(row)
        if "is_violation" in d and d["is_violation"] is not None:
            d["is_violation"] = self._to_bool(d["is_violation"])
        return SimpleNamespace(**d)

    def is_completed(self, result):
        if isinstance(result, dict):
            return result.get("status") == "completed"
        return getattr(result, "status", None) == "completed"

    async def get_moderation(self, id):
        start = time.perf_counter()
        result = await self.db.execute(
            text("SELECT * FROM moderation_results WHERE id = :id LIMIT 1"),
            {"id": id},
        )
        DB_QUERY_DURATION.labels(query_type="select_moderation").observe(time.perf_counter() - start)
        return self.to_obj(result.mappings().first())

    async def get_moderation_for_item(self, item_id):
        start = time.perf_counter()
        result = await self.db.execute(
            text("SELECT * FROM moderation_results WHERE item_id = :item_id LIMIT 1"),
            {"item_id": item_id},
        )
        DB_QUERY_DURATION.labels(query_type="select_moderation_by_item").observe(time.perf_counter() - start)
        return self.to_obj(result.mappings().first())

    async def create_moderation(self, item_id):
        start = time.perf_counter()
        result = await self.db.execute(
            text(
                "INSERT INTO moderation_results (item_id, status, retry_count) "
                "VALUES (:item_id, 'pending', 0) "
                "RETURNING *"
            ),
            {"item_id": item_id},
        )
        await self.db.commit()
        DB_QUERY_DURATION.labels(query_type="insert_moderation").observe(time.perf_counter() - start)
        return self.to_obj(result.mappings().first())

    async def get_latest_pending(self, db, item_id):
        result = await db.execute(
            text(
                "SELECT * FROM moderation_results "
                "WHERE item_id = :item_id AND status = 'pending' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"item_id": item_id},
        )
        return self.to_obj(result.mappings().first())

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
        now = datetime.now(timezone.utc)
        await db.execute(
            text(
                "UPDATE moderation_results SET "
                "status = :status, "
                "is_violation = :is_violation, "
                "probability = :probability, "
                "error_message = :error_message, "
                "retry_count = COALESCE(:retry_count, retry_count), "
                "processed_at = :processed_at "
                "WHERE id = :id"
            ),
            {
                "id": task_id,
                "status": status,
                "is_violation": is_violation,
                "probability": probability,
                "error_message": error_message,
                "retry_count": retry_count,
                "processed_at": now,
            },
        )
        await db.commit()

    async def increment_retry_count(self, db, task_id):
        result = await db.execute(
            text(
                "UPDATE moderation_results "
                "SET retry_count = retry_count + 1 "
                "WHERE id = :id "
                "RETURNING retry_count"
            ),
            {"id": task_id},
        )
        await db.commit()
        row = result.mappings().first()
        if row is None:
            return None
        return row["retry_count"]

    async def delete_moderations_for_item(self, item_id):
        result = await self.db.execute(
            text("SELECT id FROM moderation_results WHERE item_id = :item_id"),
            {"item_id": item_id},
        )
        task_ids = [row["id"] for row in result.mappings().all()]
        if task_ids:
            await self.db.execute(
                text("DELETE FROM moderation_results WHERE item_id = :item_id"),
                {"item_id": item_id},
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
