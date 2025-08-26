from fastapi import APIRouter
from .users import router as users_router
from .profile import router as profile_router
from .ws import router as ws_router
from .notifications import router as notifications_router
from .messages import router as messages_router

router = APIRouter()
router.include_router(users_router, prefix='/users', tags=['users'])
router.include_router(profile_router, prefix='/profile', tags=['profile'])
router.include_router(ws_router, prefix='/ws', tags=['ws'])
router.include_router(notifications_router, prefix='/notifications', tags=['notifications'])
router.include_router(messages_router, prefix='/messages', tags=['messages'])
