from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from model.response import PredictResponse
from model.request import PredictRequest
from service.model_service import ModelService

service = ModelService()
app = FastAPI()

@app.post("/predict")
async def get_prediction(request: PredictRequest):
    """
    Get prediction

    Args: request (PredictRequest): The prediction request containing input data

    Returns: PredictResponse: Model predictions on success (200)
             HTTPException: Error message on failure (422)
    """
    result = service.predict(request)
    return result
