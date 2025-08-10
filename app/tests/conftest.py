import pytest
from sqlalchemy import text
from app.models import engine

@pytest.fixture(autouse=True)
async def clean_db():
    # Reset tables before each test to avoid unique constraint collisions
    async with engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE session_tokens, notifications, messages, friendships, friend_requests, users RESTART IDENTITY CASCADE;"
        ))
