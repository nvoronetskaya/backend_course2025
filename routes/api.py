from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from model.request import PredictRequest
from service.model_service import ModelService
from repository.local_model_repository import LocalModelRepository
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        service.load_or_train_model()
    except OSError:
        logger.error('Failed to load model on service start')
    yield

repository = LocalModelRepository()
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
        result = service.predict(request)
        logger.info(f'Response: {result}.')
        return result
    except FileNotFoundError as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f'Got exception during prediction. Details: {str(e)}.')
        raise HTTPException(status_code=500, detail=str(e))
