from pydantic import BaseModel
from typing import Optional

class StoryCreateIn(BaseModel):
    s3_key: str
    caption: Optional[str] = None
    expires_in_seconds: int = 86400

class StoryOut(BaseModel):
    id: int
    user_id: int
    s3_key: str
    media_url: Optional[str]
    caption: Optional[str]
