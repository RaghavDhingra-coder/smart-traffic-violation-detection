# TODO for backend-application: add structured logging, auth, and startup health probes before production rollout.
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .config import settings
    from .pg_database import db_manager, initialize_tables
    from .routers.challan import router as challan_router
    from .routers.detect import router as detect_router
    from .routers.payment import router as payment_router
    from .routers.violation import router as violation_router
except ImportError:
    from config import settings
    from pg_database import db_manager, initialize_tables
    from routers.challan import router as challan_router
    from routers.detect import router as detect_router
    from routers.payment import router as payment_router
    from routers.violation import router as violation_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    db_manager.connect()
    initialize_tables()
    try:
        yield
    finally:
        db_manager.close()


app = FastAPI(
    title="Smart Traffic Violation Detection Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.backend_cors_origins == "*" else settings.backend_cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect_router)
app.include_router(challan_router)
app.include_router(payment_router)
app.include_router(violation_router)


@app.get("/")
def root():
    return {"message": "Smart Traffic Violation Detection backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
