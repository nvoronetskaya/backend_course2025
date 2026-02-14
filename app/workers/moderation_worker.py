import asyncio
import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .settings import KAFKA_BOOTSTRAP, TOPIC, DLQ_TOPIC, CONSUMER_GROUP, MLFLOW_TRACKING_URI
from db.database import session_maker
from repository.item.item_repository import ItemRepository
from repository.moderation_result.moderation_result_repository import ModerationResultRepository
from repository.model.mlflow_repository import MlflowModelRepository
from service.model_service import ModelService
from dto.request import PredictRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 3


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


def is_retryable_error(error: Exception) -> bool:
    if isinstance(error, (RetryableError, RuntimeError, ConnectionError, TimeoutError)):
        return True
    return False


def calculate_retry_delay(retry_count: int) -> int:
    return RETRY_DELAY * (2 ** retry_count)

async def main():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    
    dlq_producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP
    )
    
    model_repo = MlflowModelRepository(MLFLOW_TRACKING_URI)
    model = None
    
    try:
        model = model_repo.load_model()
    except Exception as e:
        try:
            model = model_repo.train_model()
        except Exception as train_error:
            logger.error(f"Failed to train model: {train_error}")
    
    await consumer.start()
    await dlq_producer.start()
    
    logger.info(f"[worker] Started consuming topic '{TOPIC}' as group '{CONSUMER_GROUP}'")
    try:
        async for msg in consumer:
            event = None
            item_id = None
            
            try:
                event = json.loads(msg.value.decode("utf-8"))
                item_id = event.get("item_id")
                timestamp = event.get("timestamp")
                logger.info(f"Received event: item_id={item_id}, timestamp={timestamp}")
                if item_id is None:
                    raise PermanentError("Missing 'item_id' in message")
                await process_with_retry(
                    item_id=item_id,
                    model=model,
                    model_repo=model_repo,
                    dlq_producer=dlq_producer,
                    original_event=event
                )
                await consumer.commit()
                
            except PermanentError as e:
                logger.error(f"Permanent error processing message: {e}")
                try:
                    async with session_maker() as db:
                        await mark_moderation_failed(
                            db=db,
                            item_id=item_id,
                            error_message=f"Permanent error: {str(e)}"
                        )
                except Exception as db_error:
                    logger.error(f"Failed to update moderation status: {db_error}")
                await send_to_dlq(
                    dlq_producer=dlq_producer,
                    item_id=item_id,
                    error=e,
                    event=event,
                    retry_count=0,
                    is_permanent=True
                )
                await consumer.commit()
                
            except Exception as e:
                try:
                    async with session_maker() as db:
                        await mark_moderation_failed(
                            db=db,
                            item_id=item_id,
                            error_message=str(e)
                        )
                except Exception as db_error:
                    logger.error(f"Failed to update moderation status: {db_error}")
                
                await send_to_dlq(
                    dlq_producer=dlq_producer,
                    item_id=item_id,
                    error=e,
                    event=event,
                    retry_count=0,
                    is_permanent=False
                )
                
                await consumer.commit()
                
    finally:
        await consumer.stop()
        await dlq_producer.stop()

async def process_with_retry(item_id: int, model, model_repo, dlq_producer, original_event: dict):
    retry_count = 0
    last_error = None
    
    while retry_count <= MAX_RETRIES:
        try:
            async with session_maker() as db:
                await handle_moderation(
                    db=db,
                    item_id=item_id,
                    model=model,
                    model_repo=model_repo
                )
            
            return
            
        except Exception as e:
            last_error = e
            if not is_retryable_error(e):
                raise PermanentError(str(e)) from e
            
            if retry_count >= MAX_RETRIES:
                logger.error(f"Max retries ({MAX_RETRIES}) exceeded for item_id={item_id}")
                break
            try:
                async with session_maker() as db:
                    moder_repo = ModerationResultRepository(db)
                    task = await moder_repo.get_latest_pending(db, item_id)
                    if task:
                        await moder_repo.increment_retry_count(db, task.id)
            except Exception as db_error:
                logger.warning(f"Failed to increment retry count: {db_error}")
            
            delay = calculate_retry_delay(retry_count)
            await asyncio.sleep(delay)
            retry_count += 1
    
    try:
        async with session_maker() as db:
            await mark_moderation_failed(
                db=db,
                item_id=item_id,
                error_message=f"Max retries exceeded. Last error: {str(last_error)}",
                retry_count=retry_count
            )
    except Exception as db_error:
        logger.error(f"Failed to update moderation status: {db_error}")

    await send_to_dlq(
        dlq_producer=dlq_producer,
        item_id=item_id,
        error=last_error,
        event=original_event,
        retry_count=retry_count,
        is_permanent=False
    )

async def handle_moderation(db, item_id: int, model, model_repo):
    item_repo = ItemRepository(db)
    moder_repo = ModerationResultRepository(db)
    
    item = await item_repo.get_item(item_id)
    if item is None:
        raise PermanentError(f"Item with id={item_id} not found in database")
    
    task = await moder_repo.get_latest_pending(db, item_id)
    if task is None:
        return
    if model is None:
        raise RetryableError("ML model is not available")
    prediction_request = PredictRequest(
        item_id=item.id,
        name=item.name,
        description=item.description,
        category=item.category,
        images_qty=item.images_qty
    )
    service = ModelService(
        item_repository=item_repo,
        model_repository=model_repo,
        moderation_repository=moder_repo,
        model=model
    )
    result = service.predict(prediction_request)
    await moder_repo.update_task(
        db=db,
        task_id=task.id,
        is_violation=result.is_violation,
        probability=result.probability,
        error_message=None,
        status="completed"
    )

async def mark_moderation_failed(db, item_id: int, error_message: str, retry_count: int = 0):
    if item_id is None:
        return
    
    moder_repo = ModerationResultRepository(db)
    
    task = await moder_repo.get_latest_pending(db, item_id)
    if task is None:
        logger.warning(f"No pending moderation task found for item_id={item_id}")
        return
    
    await moder_repo.update_task(
        db=db,
        task_id=task.id,
        is_violation=None,
        probability=None,
        error_message=error_message,
        status="failed",
        retry_count=retry_count
    )
    
async def send_to_dlq(dlq_producer, item_id: int, error: Exception, event: dict, retry_count: int, is_permanent: bool):
    try:
        dlq_payload = {
            "error": str(error),
            "error_type": type(error).__name__,
            "topic": TOPIC,
            "original_message": event if event else {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "item_id": item_id,
            "retry_count": retry_count,
            "max_retries": MAX_RETRIES,
            "is_permanent_error": is_permanent,
            "is_retryable": is_retryable_error(error) if not is_permanent else False
        }
        
        dlq_data = json.dumps(dlq_payload).encode("utf-8")
        await dlq_producer.send_and_wait(DLQ_TOPIC, dlq_data)
        logger.info(f"Sent message to DLQ: item_id={item_id}, retries={retry_count}, permanent={is_permanent}")
        
    except Exception as dlq_error:
        logger.error(f"Failed to send to DLQ: {dlq_error}")

if __name__ == "__main__":
    asyncio.run(main())
