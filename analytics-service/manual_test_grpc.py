"""Phase 12 gRPC check for the Analytics service.

  cd analytics-service && ../.venv/Scripts/python manual_test_grpc.py
"""

import asyncio
import warnings

warnings.filterwarnings("ignore")

import grpc
from sqlalchemy import func, select

from app.db import engine
from app.grpc_server import serve_grpc
from echoscope_db.models import Mention
from echoscope_rpc import analytics_pb2, analytics_pb2_grpc, grpc_status_to_http

PORT = 50151


async def main() -> None:
    out = []
    async with engine.connect() as conn:
        org_id = str((await conn.execute(
            select(Mention.org_id).group_by(Mention.org_id).order_by(func.count().desc()).limit(1)
        )).scalar_one())

    server = await serve_grpc(PORT)
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{PORT}") as ch:
            stub = analytics_pb2_grpc.AnalyticsServiceStub(ch)

            s = await stub.GetAnalyticsSummary(analytics_pb2.SummaryRequest(org_id=org_id))
            assert s.total_mentions > 0
            out.append(f"GetAnalyticsSummary -> total={s.total_mentions}, pos%={s.positive_pct:.3f}, spike={s.spike_detected}")

            t = await stub.GetTrends(analytics_pb2.TrendsRequest(org_id=org_id, granularity="day"))
            assert len(t.datapoints) > 0
            out.append(f"GetTrends(day) -> {len(t.datapoints)} datapoints")

            m = await stub.GetCurrentMetrics(analytics_pb2.MetricsRequest(org_id=org_id))
            assert m.total_mentions >= 0
            out.append(f"GetCurrentMetrics -> total={m.total_mentions}, spike_count={m.spike_count}")
    finally:
        await server.stop(grace=1)
        await engine.dispose()

    assert grpc_status_to_http(grpc.StatusCode.NOT_FOUND) == 404
    assert grpc_status_to_http(grpc.StatusCode.UNAVAILABLE) == 503
    out.append("grpc_status_to_http: NOT_FOUND->404, UNAVAILABLE->503")

    print("\n".join("PASS  " + s for s in out))
    print("\nANALYTICS gRPC CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
