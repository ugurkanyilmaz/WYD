import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url='http://test') as ac:
        res = await ac.get('/api/users/1')
        assert res.status_code in (200,404)
