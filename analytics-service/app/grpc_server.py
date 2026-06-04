"""Analytics gRPC server (HLD §9/§12).

RPCs: GetAnalyticsSummary, GetTrends, GetCurrentMetrics — backed by the same Pandas
computations as the REST API. Runs on an internal-only port alongside FastAPI.
"""

from __future__ import annotations

from datetime import datetime

import grpc
from loguru import logger as log

from app import analytics as A
from config import get_settings
from echoscope_rpc import analytics_pb2, analytics_pb2_grpc


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class AnalyticsServicer(analytics_pb2_grpc.AnalyticsServiceServicer):
    async def GetAnalyticsSummary(self, request, context):
        f = _parse(request.from_date) or A.default_range(30)[0]
        t = _parse(request.to_date) or A.default_range(0)[1]
        df = await A.load_frame(request.org_id, f, t)
        ov = A.overview(df, f, t)
        spikes = A.detect_spikes(df, threshold=get_settings().spike_threshold)["spikes"]
        return analytics_pb2.SummaryResponse(
            total_mentions=ov["total_mentions"],
            positive_pct=ov["positive_pct"],
            negative_pct=ov["negative_pct"],
            avg_per_day=ov["avg_per_day"],
            spike_detected=len(spikes) > 0,
        )

    async def GetTrends(self, request, context):
        f = _parse(request.from_date) or A.default_range(30)[0]
        t = A.default_range(0)[1]
        df = await A.load_frame(request.org_id, f, t)
        tr = A.trends(df, request.granularity or "day")
        pts = [
            analytics_pb2.TrendPoint(
                time=p["time"], count=p["count"], positive=p["positive"],
                negative=p["negative"], neutral=p["neutral"],
            )
            for p in tr["datapoints"]
        ]
        return analytics_pb2.TrendsResponse(datapoints=pts)

    async def GetCurrentMetrics(self, request, context):
        f, t = A.default_range(7)
        df = await A.load_frame(request.org_id, f, t)
        ov = A.overview(df, f, t)
        spikes = A.detect_spikes(df, threshold=get_settings().spike_threshold)["spikes"]
        return analytics_pb2.MetricsResponse(
            total_mentions=ov["total_mentions"],
            positive_pct=ov["positive_pct"],
            negative_pct=ov["negative_pct"],
            spike_count=len(spikes),
        )


async def serve_grpc(port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    analytics_pb2_grpc.add_AnalyticsServiceServicer_to_server(AnalyticsServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    log.info("analytics gRPC server started", port=port)
    return server
