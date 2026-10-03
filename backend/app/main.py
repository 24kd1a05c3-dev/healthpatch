import logging
import time
import re
import asyncio
from contextlib import suppress, asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import connect_db, close_db
from app.routers import auth, users, devices, health_data, alerts, emergency, replay, websocket
from app.config import settings
from app.routers import workspace
from app.routers import simulation
from app.routers import notifications
from app.routers import operations
from app.request_context import JsonFormatter, request_id_context
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("healthpatch")
logging.getLogger('twilio').setLevel(logging.CRITICAL)
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())

production = settings.ENVIRONMENT.lower() == 'production'


@asynccontextmanager
async def lifespan(application):
    await startup()
    try:
        yield
    finally:
        await shutdown()


app = FastAPI(title="HealthPatch API", description="Backend for HealthPatch monitoring system", version="1.0.0",
              docs_url=None if production else '/docs', redoc_url=None if production else '/redoc',
              openapi_url=None if production else '/openapi.json', lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    supplied_id = request.headers.get('x-request-id', '')
    request_id = supplied_id if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', supplied_id) else str(uuid4())
    context_token = request_id_context.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            "Unhandled request error",
            extra={"request_id": request_id, "error_type": type(error).__name__, "method": request.method},
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"x-request-id": request_id},
        )
    finally:
        request_id_context.reset(context_token)
    response.headers["x-request-id"] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    if production:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "route": getattr(request.scope.get('route'), 'path', 'unmatched'),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response

async def startup():
    await connect_db()
    from app.database import db_manager
    from app.services.telemetry_service import recovery_loop
    from app.services.telephone_service import notification_loop
    app.state.recovery_task = asyncio.create_task(recovery_loop(db_manager.db))
    app.state.notification_task = asyncio.create_task(notification_loop(db_manager.db))


async def shutdown():
    for name in ('recovery_task', 'notification_task'):
        task = getattr(app.state, name, None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    await close_db()



app.include_router(auth.router)
app.include_router(users.router)
app.include_router(devices.router)
app.include_router(health_data.router)
app.include_router(alerts.router)
app.include_router(emergency.router)
app.include_router(replay.router)
app.include_router(websocket.router)
app.include_router(workspace.router)
app.include_router(simulation.router)
app.include_router(notifications.router)
app.include_router(operations.router)

@app.get("/")
async def root():
    return {"message": "Welcome to HealthPatch API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get('/ready')
async def ready():
    from app.database import db_manager
    try:
        await db_manager.client.admin.command('ping')
        for name in ('recovery_task', 'notification_task'):
            task = getattr(app.state, name, None)
            if task is None or task.done():
                return JSONResponse(status_code=503, content={'status': 'worker_unavailable'})
    except Exception:
        return JSONResponse(status_code=503, content={'status': 'unavailable'})
    return {'status': 'ready'}
