from pydantic import BaseModel, Field, StrictInt
from typing import Annotated

class Item(BaseModel):
    id: Annotated[StrictInt, Field(ge=0)]
    name: Annotated[str, Field(min_length=1)]
    description: Annotated[str, Field(min_length=1)]
    category: Annotated[StrictInt, Field(ge=0)]
    images_qty: Annotated[StrictInt, Field(ge=0)] 
