import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from dto.request import PredictRequest
from dto.response import AsyncPredictResponse, ModerationResultResponse
from service.model_service import ModelService
from service.moderation_service import ModerationService
from repository.model.mlflow_repository import MlflowModelRepository
from repository.item.item_repository import ItemRepository
from repository.moderation_result.moderation_result_repository import ModerationResultRepository
import logging
import mlflow
import os
import sentry_sdk
from starlette.concurrency import run_in_threadpool
from db.database import get_db, session_maker, engine, Base
from utils import load_synthetic_data
from app.clients.kafka import KafkaProducer
from app.clients.settings import KAFKA_BOOTSTRAP
from repository.moderation_result.moderation_redis_repository import ModerationRedisRepository
from app.clients.middleware import PrometheusMiddleware, generate_latest, CONTENT_TYPE_LATEST
from app.metrics import (
    PREDICTIONS_TOTAL,
    PREDICTION_DURATION,
    PREDICTION_ERRORS_TOTAL,
    DB_QUERY_DURATION,
    MODEL_PREDICTION_PROBABILITY,
)
from app.exceptions import ModelIsNotAvailable, ErrorInPrediction, AdvertisementNotFoundError
from fastapi import Response
import time

ML_MODEL = None
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
logger = logging.getLogger(__name__)
producer = KafkaProducer(KAFKA_BOOTSTRAP)
redis_repo = ModerationRedisRepository()

def get_model_service(db = Depends(get_db)):
    return ModelService(
        item_repository=ItemRepository(db), 
        model_repository=model_repository, 
        model=ML_MODEL
    )

def get_moderation_service(db = Depends(get_db)):
    return ModerationService(
        item_repo=ItemRepository(db), 
        moder_repo=ModerationResultRepository(db),
        redis_repo=redis_repo,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ML_MODEL
    sentry_sdk.init(
        # Тут должен быть ключ от Sentry
        dsn=os.getenv("SENTRY_DSN", ""),
        traces_sample_rate=1.0,
        environment=os.getenv("SENTRY_ENVIRONMENT", "dev"),
    )
    logger.info("Setting up MLflow tracking")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
    mlflow.sklearn.autolog(disable=True)
    await producer.start()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_maker() as db:
            item_repo = ItemRepository(db)
            await load_synthetic_data(item_repo)
            service = ModelService(
                item_repository=item_repo, 
                model_repository=model_repository,
            )
            try:
                await asyncio.wait_for(
                    run_in_threadpool(service.load_model),
                    timeout=5,
                )
                logger.info("Model loaded successfully")
                ML_MODEL = service.model
            except (TimeoutError, RuntimeError, asyncio.TimeoutError):
                logger.info('Model was not found in MLFlow or timeout. Training a new one')
                await run_in_threadpool(service.train_model)
                ML_MODEL = service.model
            except Exception as e:
                logger.exception(f'Failed to load model on service start: {e}')
        yield
    finally:
        await producer.stop()

model_repository = MlflowModelRepository(MLFLOW_TRACKING_URI)

if os.getenv("TESTING"):
    app = FastAPI()
else:
    app = FastAPI(lifespan=lifespan)

@app.post("/predict")
async def get_prediction(request: PredictRequest, service = Depends(get_model_service)):
    """
    Get prediction

    Args: request (PredictRequest): The prediction request containing input data

    Returns: PredictResponse: Model predictions on success (200)
             HTTPException: Error message on failure (422)
    """
    logger.info(f'Got new request: {request}.')
    start = time.perf_counter()
    try:
        result = await run_in_threadpool(service.predict, request)
        PREDICTION_DURATION.observe(time.perf_counter() - start)
        PREDICTIONS_TOTAL.labels(result="violation" if result.is_violation else "no_violation").inc()
        MODEL_PREDICTION_PROBABILITY.observe(result.probability)
        logger.info(f'Response: {result}.')
        return result
    except ModelIsNotAvailable as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="model_not_found").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except ErrorInPrediction as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="internal").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simple_predict/{item_id}")
async def get_prediction_for_id(item_id: int, model_service = Depends(get_model_service), moder_service = Depends(get_moderation_service)):
    """
    Get prediction

    Args: request (PredictRequest): The prediction request containing input data
    Returns: PredictResponse: Model predictions on success (200)
             HTTPException: Error message on failure (422)
    """
    logger.info(f'Got new prediciton request for item with id {item_id}.')
    try:
        result = await moder_service.get_prediction_for_item(item_id)
        from_cache = result is not None
        
        if result is None:
            start = time.perf_counter()
            result = await model_service.get_prediction_for_item(item_id)
            if result is not None:
                PREDICTION_DURATION.observe(time.perf_counter() - start)
        
        if result is None:
            raise AdvertisementNotFoundError(f"Item with id={item_id} not found")
        
        if not from_cache:
            await moder_service.save_prediction_to_cache(item_id, result)
        
        is_violation = result.get("is_violation") if isinstance(result, dict) else result.is_violation
        probability = result.get("probability") if isinstance(result, dict) else result.probability
        PREDICTIONS_TOTAL.labels(result="violation" if is_violation else "no_violation").inc()
        if probability is not None:
            MODEL_PREDICTION_PROBABILITY.observe(probability)
        logger.info(f'Response: {result}.')
        return result
    except AdvertisementNotFoundError as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="item_not_found").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=404, detail=str(e))
    except ModelIsNotAvailable as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="model_not_found").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except ErrorInPrediction as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="internal").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/async_predict/{item_id}")
async def get_async_prediction_for_id(item_id: int, service = Depends(get_moderation_service)):
    """
    Create async moderation request for item

    Args: item_id (int): The item ID to moderate

    Returns: AsyncPredictResponse: Task information on success (200)
             HTTPException: Error message on failure (404, 500)
    """
    logger.info(f'Got new async prediction request for item with id {item_id}.')
    try:
        task_id = await service.get_moderation_task_id_for_item(item_id)
        if task_id is None:
            raise HTTPException(status_code=404, detail="Item with id is not found")
        await producer.send_moderation_request(item_id)
        logger.info(f'Created moderation task id: {task_id}.')
        return AsyncPredictResponse(
            task_id=task_id,
            status="pending",
            message="Moderation request accepted"
        )
    except HTTPException:
        PREDICTION_ERRORS_TOTAL.labels(error_type="item_not_found").inc()
        raise
    except AdvertisementNotFoundError as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="item_not_found").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="internal").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/moderation_result/{task_id}")
async def get_moderation_result(task_id: int, service = Depends(get_moderation_service)):
    """
    Get moderation result by task ID

    Args: task_id (int): The moderation task ID

    Returns: ModerationResultResponse: Moderation result on success (200)
             HTTPException: Error message on failure (404, 500)
    """
    try:
        task = await service.get_moderation_result(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task with id is not found")
        if isinstance(task, dict):
            prob = task.get("probability")
            if prob is not None:
                MODEL_PREDICTION_PROBABILITY.observe(prob)
            return ModerationResultResponse(
                task_id=task["id"],
                status=task["status"],
                is_violation=task.get("is_violation"),
                probability=prob
            )
        if task.probability is not None:
            MODEL_PREDICTION_PROBABILITY.observe(task.probability)
        return ModerationResultResponse(
            task_id=task.id,
            status=task.status,
            is_violation=task.is_violation,
            probability=task.probability
        )
    except HTTPException:
        raise
    except Exception as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="internal").inc()
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/close/{item_id}")
async def close_item(item_id: int, service = Depends(get_moderation_service)):
    """
    Close an item listing

    Marks the item as closed and removes all associated moderation results
    from both PostgreSQL and Redis cache.

    Args: item_id (int): The item ID to close

    Returns: dict with message and item_id on success (200)
             HTTPException: 404 if item not found, 500 on error
    """
    try:
        result = await service.close_item(item_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Item closed", "item_id": item_id}
    except HTTPException:
        raise
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f'Error closing item {item_id}: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

app.add_middleware(PrometheusMiddleware)

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
