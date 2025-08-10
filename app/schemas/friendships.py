from pydantic import BaseModel

class FriendRequestOut(BaseModel):
    id: int
    from_user: int
    to_user: int
    status: str | None = None

    class Config:
        orm_mode = True

class FriendshipOut(BaseModel):
    id: int
    user_id: int
    friend_id: int

    class Config:
        orm_mode = True

class AreFriendsOut(BaseModel):
    friends: bool

class ActionOkOut(BaseModel):
    ok: bool
