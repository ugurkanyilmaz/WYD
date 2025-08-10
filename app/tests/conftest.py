import pytest
import pytest_asyncio
import os
import sys
from pathlib import Path

# Configure test environment (use docker service hostname by default)
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://social:socialpass@postgres:5432/socialdb')      

# Ensure the package root is on sys.path when pytest changes CWD to this tests dir
HERE = Path(__file__).resolve()
PKG_ROOT = HERE.parents[2]  # /usr/src
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
