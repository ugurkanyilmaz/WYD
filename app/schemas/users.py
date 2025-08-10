from pydantic import BaseModel, EmailStr
from typing import Optional

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
    refresh_token: str | None = None

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
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip: Optional[str] = None

class RefreshIn(BaseModel):
    refresh_token: str

class LogoutIn(BaseModel):
    refresh_token: str
