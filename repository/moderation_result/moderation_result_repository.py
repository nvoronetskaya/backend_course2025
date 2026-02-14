from sqlalchemy import select
from datetime import datetime, timezone
from db.tables.moderation_result import ModerationResult

class ModerationResultRepository:
    def __init__(self, db):
        self.db = db

    async def get_moderation(self, id):
        result = await self.db.execute(select(ModerationResult).where(ModerationResult.id == id).limit(1))
        return result.scalars().first()

    async def create_moderation(self, item_id):
        db_moderation = ModerationResult(
            item_id=item_id,
            status="pending",
            retry_count=0
        )
        self.db.add(db_moderation)
        await self.db.commit()
        await self.db.refresh(db_moderation)
        return db_moderation.id
    
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