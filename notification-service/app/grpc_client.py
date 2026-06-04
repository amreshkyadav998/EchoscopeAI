"""gRPC client → Analytics service (HLD §9). Best-effort: returns None on failure."""

from __future__ import annotations

from loguru import logger as log

from config import get_settings
from echoscope_rpc import analytics_pb2, analytics_pb2_grpc, channel, with_retry


async def get_current_metrics(org_id: str) -> dict | None:
    """Fetch live metrics to enrich an alert. None if the analytics gRPC is unavailable."""
    addr = get_settings().analytics_grpc_addr
    try:
        async with channel(addr) as ch:
            stub = analytics_pb2_grpc.AnalyticsServiceStub(ch)
            resp = await with_retry(
                lambda: stub.GetCurrentMetrics(analytics_pb2.MetricsRequest(org_id=org_id))
            )
            return {
                "total_mentions": resp.total_mentions,
                "positive_pct": round(resp.positive_pct, 4),
                "negative_pct": round(resp.negative_pct, 4),
                "spike_count": resp.spike_count,
            }
    except Exception as exc:
        log.warning("analytics gRPC unavailable; alert not enriched", error=str(exc))
        return None
