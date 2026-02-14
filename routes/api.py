import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from dto.request import PredictRequest
from dto.response import AsyncPredictResponse, ModerationResultResponse
from service.model_service import ModelService
from repository.model.mlflow_repository import MlflowModelRepository
from repository.item.item_repository import ItemRepository
from repository.moderation_result.moderation_result_repository import ModerationResultRepository
import logging
import mlflow
import os
from starlette.concurrency import run_in_threadpool
from db.database import get_db, session_maker, engine, Base
from db.tables import seller, item, moderation_result
from utils import load_synthetic_data
from app.clients.kafka import KafkaProducer
from app.clients.settings import KAFKA_BOOTSTRAP

ML_MODEL = None
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
logger = logging.getLogger(__name__)
producer = KafkaProducer(KAFKA_BOOTSTRAP)

def get_service(db = Depends(get_db)):
    return ModelService(
        item_repository=ItemRepository(db), 
        model_repository=model_repository, 
        moderation_repository=ModerationResultRepository(db),
        model=ML_MODEL
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ML_MODEL
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
            moderation_repo = ModerationResultRepository(db)
            service = ModelService(
                item_repository=item_repo, 
                model_repository=model_repository,
                moderation_repository=moderation_repo
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
async def get_prediction(request: PredictRequest, service = Depends(get_service)):
    """
    Get prediction

    Args: request (PredictRequest): The prediction request containing input data

    Returns: PredictResponse: Model predictions on success (200)
             HTTPException: Error message on failure (422)
    """
    logger.info(f'Got new request: {request}.')
    try:
        result = await run_in_threadpool(service.predict, request)
        logger.info(f'Response: {result}.')
        return result
    except FileNotFoundError as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simple_predict/{item_id}")
async def get_prediction_for_id(item_id: int, service = Depends(get_service)):
    """
    Get prediction

    Args: request (PredictRequest): The prediction request containing input data
    Returns: PredictResponse: Model predictions on success (200)
             HTTPException: Error message on failure (422)
    """
    logger.info(f'Got new prediciton request for item with id {item_id}.')
    try:
        result = await service.get_prediction_for_item(item_id)
        if result is None:
            raise FileNotFoundError(0)
        logger.info(f'Response: {result}.')
        return result
    except FileNotFoundError as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/async_predict/{item_id}")
async def get_async_prediction_for_id(item_id: int, service = Depends(get_service)):
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
        raise
    except FileNotFoundError as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/moderation_result/{task_id}")
async def get_moderation_result(task_id: int, service = Depends(get_service)):
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
        return ModerationResultResponse(
            task_id=task.id,
            status=task.status,
            is_violation=task.is_violation,
            probability=task.probability
        )
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))