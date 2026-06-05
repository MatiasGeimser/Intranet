from pydantic import BaseModel, Field
from typing import Optional

class AreaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None

class AreaCreate(AreaBase):
    pass

class AreaSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class AreaOut(AreaBase):
    id: int

    class Config:
        from_attributes = True
