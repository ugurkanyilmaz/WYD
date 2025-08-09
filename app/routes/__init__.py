from fastapi import APIRouter
from .users import router as users_router
from .posts import router as posts_router
from .ws import router as ws_router
from .notifications import router as notifications_router

router = APIRouter()
router.include_router(users_router, prefix='/users', tags=['users'])
router.include_router(posts_router, prefix='/posts', tags=['posts'])
router.include_router(ws_router, prefix='/ws', tags=['ws'])
router.include_router(notifications_router, prefix='/notifications', tags=['notifications'])
