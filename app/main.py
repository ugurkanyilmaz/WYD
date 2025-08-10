import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .core import kafka_startup, redis_startup, init_metrics, mongo_startup
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from pythonjsonlogger import jsonlogger

# setup structured logging
logger = logging.getLogger('socialapp')
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="SocialApp API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router, prefix="/api")

@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}

@app.middleware('http')
async def log_requests(request: Request, call_next):
    logger.info({'msg':'request_start','method':request.method,'path':request.url.path})
    response = await call_next(request)
    logger.info({'msg':'request_end','status': response.status_code})
    return response

@app.on_event("startup")
async def startup():
    # Best-effort init, don't block app from starting if a dependency fails
    try:
        await redis_startup()
    except Exception as e:
        logger.warning({'msg': 'redis_start_failed', 'error': str(e)})
    try:
        await kafka_startup()
    except Exception as e:
        logger.warning({'msg': 'kafka_start_failed', 'error': str(e)})
    try:
        init_metrics()
    except Exception as e:
        logger.warning({'msg': 'metrics_init_failed', 'error': str(e)})
    try:
        await mongo_startup()
    except Exception as e:
        logger.warning({'msg': 'mongo_init_failed', 'error': str(e)})

@app.on_event("shutdown")
async def shutdown():
    pass
