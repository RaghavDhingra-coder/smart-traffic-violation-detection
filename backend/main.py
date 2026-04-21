# TODO for backend-application: add structured logging, auth, and startup health probes before production rollout.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers.challan import router as challan_router
from routers.detect import router as detect_router
from routers.payment import router as payment_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Traffic Violation Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # STUB: replace with real implementation using explicit frontend origins.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect_router)
app.include_router(challan_router)
app.include_router(payment_router)


@app.get("/")
async def root():
    return {"message": "Traffic Violation Detection Backend is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
