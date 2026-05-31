"""Health endpoint.

For now returns the gateway's own status. In Phase 2.4 this will also poll each
downstream service's /health (used by the ALB target group health check, HLD 4.1).
"""

from __future__ import annotations

from fastapi import APIRouter

from config import get_settings
from echoscope_common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.service_name,
        version="0.1.0",
        checks={"gateway": "ok"},
    )
