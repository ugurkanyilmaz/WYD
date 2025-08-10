from fastapi import APIRouter
from .users import router as users_router
from .posts import router as posts_router
from .ws import router as ws_router
from .notifications import router as notifications_router
from .stories import router as stories_router
from .messages import router as messages_router

router = APIRouter()
router.include_router(users_router, prefix='/users', tags=['users'])
router.include_router(posts_router, prefix='/posts', tags=['posts'])
router.include_router(ws_router, prefix='/ws', tags=['ws'])
router.include_router(notifications_router, prefix='/notifications', tags=['notifications'])
router.include_router(stories_router, prefix='/stories', tags=['stories'])
router.include_router(messages_router, prefix='/messages', tags=['messages'])
