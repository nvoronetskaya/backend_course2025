from pydantic import BaseModel, Field
from typing import Annotated


class LoginRequest(BaseModel):
    login: Annotated[str, Field(min_length=1)]
    password: Annotated[str, Field(min_length=1)]
