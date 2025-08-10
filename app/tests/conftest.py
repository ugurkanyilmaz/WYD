import pytest
import pytest_asyncio
import os

# Configure test environment
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://social:socialpass@localhost:5432/socialdb')

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
