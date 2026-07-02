"""FastAPI application entry point for the AI Incident Timeline Correlator."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings  # noqa: F401 - ensures .env is loaded at startup
from app.routers import investigate

app = FastAPI(
    title="AI Incident Timeline Correlator",
    description="Correlates GitHub commits with AWS CloudWatch data to identify incident root causes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigate.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "incident-timeline-correlator"}
