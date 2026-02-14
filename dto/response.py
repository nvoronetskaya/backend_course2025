from pydantic import BaseModel
from typing import Optional

class PredictResponse(BaseModel):
    """
    Pydantic model for the prediction result

    Attributes:
        has_errors (bool): Determines whether the item ad has errors
    """
    is_violation: bool
    probability: float

class AsyncPredictResponse(BaseModel):
    """
    Pydantic model for async prediction request response
    
    Attributes:
        task_id (int): ID of the moderation task
        status (str): Current status of the task
        message (str): Message about the request
    """
    task_id: int
    status: str
    message: str

class ModerationResultResponse(BaseModel):
    """
    Pydantic model for moderation result
    
    Attributes:
        task_id (int): ID of the moderation task
        status (str): Current status of the task
        is_violation (Optional[bool]): Whether the item violates rules
        probability (Optional[float]): Probability of violation
    """
    task_id: int
    status: str
    is_violation: Optional[bool]
    probability: Optional[float]
