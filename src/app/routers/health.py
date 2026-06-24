"""Health check endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}
