"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import tickets

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="TriageAI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "triage_enabled": settings.triage_enabled,
        "triage_model": settings.triage_model if settings.triage_enabled else None,
    }
