from pydantic import BaseModel
from typing import Optional

class PostIn(BaseModel):
    content: str

class PostOut(BaseModel):
    id: int
    author_id: int
    content: str

class CommentIn(BaseModel):
    post_id: int
    content: str
    parent_id: Optional[int]
