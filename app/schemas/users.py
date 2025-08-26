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
    profile_picture_url: Optional[str]
    bio: Optional[str]  # Bio field

    class Config:
        orm_mode = True

class LoginIn(BaseModel):
    username: str
    password: str
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip: Optional[str] = None

class RefreshIn(BaseModel):
    refresh_token: str

# Profile Management Schemas
class ProfileUpdateIn(BaseModel):
    bio: Optional[str] = None
    display_name: Optional[str] = None

class ProfilePictureUploadOut(BaseModel):
    profile_picture_url: str
    message: str

class ActionOkOut(BaseModel):
    ok: bool = True
    message: Optional[str] = None

class LogoutIn(BaseModel):
    refresh_token: str
