from pydantic import BaseModel, Field
from typing import Annotated

class PredictRequest(BaseModel):
    """
    Pydantic model for making predictions

    This request model contains the input data for which prediction is requested

    Attributes:
        seller_id (int): Unique identifier of the seller
        is_verified_seller (bool): If the seller of the item has a verified account
        item_id (int): Unique identifier of an item
        name (str): Name of the item
        description (str): Description of the item
        category (int): Description of the item
        images_qty (int): Number of images in the item ad
    """

    seller_id: Annotated[int, Field(ge=0)]
    is_verified_seller: bool
    item_id: Annotated[int, Field(ge=0)]
    name: Annotated[str, Field(min_length=1)]
    description: Annotated[str, Field(min_length=1)]
    category: Annotated[int, Field(ge=0)]
    images_qty: Annotated[int, Field(ge=0)] 
