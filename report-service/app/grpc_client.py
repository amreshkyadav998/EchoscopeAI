"""gRPC client → Analytics service (HLD §9). Best-effort: returns None on failure."""

from __future__ import annotations

from loguru import logger as log

from config import get_settings
from echoscope_rpc import analytics_pb2, analytics_pb2_grpc, channel, with_retry


async def get_analytics_summary(org_id: str) -> dict | None:
    """Fetch a live analytics summary to embed in the report. None if unavailable."""
    addr = get_settings().analytics_grpc_addr
    try:
        async with channel(addr) as ch:
            stub = analytics_pb2_grpc.AnalyticsServiceStub(ch)
            resp = await with_retry(
                lambda: stub.GetAnalyticsSummary(analytics_pb2.SummaryRequest(org_id=org_id))
            )
            return {
                "total_mentions": resp.total_mentions,
                "positive_pct": round(resp.positive_pct, 4),
                "negative_pct": round(resp.negative_pct, 4),
                "avg_per_day": round(resp.avg_per_day, 2),
                "spike_detected": resp.spike_detected,
            }
    except Exception as exc:
        log.warning("analytics gRPC unavailable; report omits live summary", error=str(exc))
        return None
