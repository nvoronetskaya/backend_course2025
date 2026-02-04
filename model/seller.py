from pydantic import BaseModel, Field, StrictInt
from typing import Annotated

class Seller(BaseModel):
    id: Annotated[StrictInt, Field(ge=0)]
    is_verified_seller: bool
