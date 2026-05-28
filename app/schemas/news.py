from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)

class CommentCreate(CommentBase):
    pass

class AuthorSimple(BaseModel):
    id: int
    full_name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class CommentResponse(CommentBase):
    id: int
    news_id: int
    author_id: int
    author: AuthorSimple
    created_at: datetime

    class Config:
        from_attributes = True


class NewsBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=10)
    category: str = Field("General", max_length=50)
    is_featured: Optional[bool] = False

class NewsCreate(NewsBase):
    pass

class NewsUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, max_length=50)
    is_featured: Optional[bool] = None

class NewsResponse(NewsBase):
    id: int
    author_id: int
    author: AuthorSimple
    comments: List[CommentResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
