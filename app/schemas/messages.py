from pydantic import BaseModel

class MessageIn(BaseModel):
    recipient_id: int
    content: str

class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str
