import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from model.request import PredictRequest
from service.model_service import ModelService
from repository.mlflow_repository import MlflowModelRepository
import logging
import mlflow
import os
from starlette.concurrency import run_in_threadpool

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Setting up MLflow tracking")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
    mlflow.sklearn.autolog(disable=True)
    try:
        await asyncio.wait_for(
            run_in_threadpool(service.load_model),
            timeout=5,
        )
    except (TimeoutError, RuntimeError):
        logger.info('Model was not found in MLFlow. Training a new one')
        await run_in_threadpool(service.train_model)
    except Exception:
        logger.exception('Failed to load model on service start')
    yield

repository = MlflowModelRepository(MLFLOW_TRACKING_URI)
service = ModelService(repository)
app = FastAPI(lifespan=lifespan)

@app.post("/predict")
async def get_prediction(request: PredictRequest):
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
