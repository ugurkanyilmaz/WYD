from pydantic import BaseModel, EmailStr
from typing import Optional, List

class RegisterIn(BaseModel):
    username: str
    name: str
    surname: str
    email: EmailStr
    phone_number: str
    password: str
    display_name: Optional[str]

class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class UserOut(BaseModel):
    id: int
    username: str
    name: str
    surname: str
    email: EmailStr
    phone_number: str
    display_name: Optional[str]
    avatar_url: Optional[str]

class LoginIn(BaseModel):
    username: str
    password: str

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
