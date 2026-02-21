import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from db.database import Base
from db.tables.item import Item as DbItem
from db.tables.moderation_result import ModerationResult
from repository.item.item_repository import ItemRepository
from repository.moderation_result.moderation_result_repository import ModerationResultRepository

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
def item_repo(db_session):
    return ItemRepository(db_session)

@pytest.fixture
def moder_repo(db_session):
    return ModerationResultRepository(db_session)

async def seed_item(db_session, **overrides):
    defaults = dict(
        name="Test Item",
        description="Test description",
        category=1,
        images_qty=5,
    )
    defaults.update(overrides)
    item = DbItem(**defaults)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item

@pytest.mark.integration
class TestItemRepository:
    async def test_create_and_get_item(self, db_session, item_repo):
        item = await seed_item(
            db_session,
            name="Wireless Earbuds",
            description="Compact TWS earbuds",
            category=2,
            images_qty=7,
        )
        fetched = await item_repo.get_item(item.id)
        assert fetched is not None
        assert fetched.id == item.id
        assert fetched.name == "Wireless Earbuds"
        assert fetched.description == "Compact TWS earbuds"
        assert fetched.category == 2
        assert fetched.images_qty == 7
        assert fetched.is_closed is False

    async def test_get_item_not_found(self, item_repo):
        result = await item_repo.get_item(999999)
        assert result is None

    async def test_close_item(self, db_session, item_repo):
        item = await seed_item(db_session)
        assert item.is_closed is False
        closed = await item_repo.close_item(item.id)
        assert closed is not None
        assert closed.is_closed is True
        assert closed.id == item.id

    async def test_close_item_not_found(self, item_repo):
        result = await item_repo.close_item(999999)
        assert result is None

    async def test_close_item_is_idempotent(self, db_session, item_repo):
        item = await seed_item(db_session)
        await item_repo.close_item(item.id)
        closed_again = await item_repo.close_item(item.id)
        assert closed_again is not None
        assert closed_again.is_closed is True

@pytest.mark.integration
class TestModerationResultRepository:
    async def test_create_and_get_moderation(self, db_session, moder_repo):
        item = await seed_item(db_session)
        task = await moder_repo.create_moderation(item.id)
        assert task is not None
        assert task.item_id == item.id
        assert task.status == "pending"
        assert task.retry_count == 0
        fetched = await moder_repo.get_moderation(task.id)
        assert fetched is not None
        assert fetched.id == task.id

    async def test_get_moderation_for_item(self, db_session, moder_repo):
        item = await seed_item(db_session)
        task = await moder_repo.create_moderation(item.id)
        fetched = await moder_repo.get_moderation_for_item(item.id)
        assert fetched is not None
        assert fetched.id == task.id
        assert fetched.item_id == item.id

    async def test_get_moderation_not_found(self, moder_repo):
        result = await moder_repo.get_moderation(999999)
        assert result is None

    async def test_get_moderation_for_item_not_found(self, moder_repo):
        result = await moder_repo.get_moderation_for_item(999999)
        assert result is None

    async def test_delete_moderations_for_item(self, db_session, moder_repo):
        item = await seed_item(db_session)
        t1 = await moder_repo.create_moderation(item.id)
        t2 = await moder_repo.create_moderation(item.id)
        t3 = await moder_repo.create_moderation(item.id)
        deleted_ids = await moder_repo.delete_moderations_for_item(item.id)
        assert sorted(deleted_ids) == sorted([t1.id, t2.id, t3.id])
        assert await moder_repo.get_moderation(t1.id) is None
        assert await moder_repo.get_moderation(t2.id) is None
        assert await moder_repo.get_moderation(t3.id) is None

    async def test_delete_moderations_for_item_no_results(self, db_session, moder_repo):
        item = await seed_item(db_session)
        deleted_ids = await moder_repo.delete_moderations_for_item(item.id)
        assert deleted_ids == []

    async def test_delete_moderations_does_not_affect_other_items(self, db_session, moder_repo):
        item_a = await seed_item(db_session, name="Item A")
        item_b = await seed_item(db_session, name="Item B")
        await moder_repo.create_moderation(item_a.id)
        task_b = await moder_repo.create_moderation(item_b.id)
        await moder_repo.delete_moderations_for_item(item_a.id)
        assert await moder_repo.get_moderation(task_b.id) is not None
        assert await moder_repo.get_moderation_for_item(item_b.id) is not None
