# Authentication schemas will be defined here.
from pydantic import BaseModel, Field

# Schema for user registration
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6)

# Schema for user login
class UserLogin(BaseModel):
    username: str
    password: str

# JWT Token structure
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Data decoded from JWT
class TokenData(BaseModel):
    user_id: int | None = None
