# app/schemas/user.py
from pydantic import BaseModel

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    profile_photo: str | None = None  # URL or path to the user's profile photo

    class Config:
        orm_mode = True
