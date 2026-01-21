from pydantic import BaseModel

class PredictResponse(BaseModel):
    """
    Pydantic model for the prediction result

    Attributes:
        has_errors (bool): Determines whether the item ad has errors
    """
    has_errors: bool
