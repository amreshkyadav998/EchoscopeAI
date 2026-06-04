"""Phase 12 gRPC check for the NLP service.

  cd nlp-service && ../.venv/Scripts/python manual_test_grpc.py
"""

import asyncio
import warnings

warnings.filterwarnings("ignore")

import grpc

from app.grpc_server import serve_grpc
from echoscope_rpc import nlp_pb2, nlp_pb2_grpc

PORT = 50152


async def main() -> None:
    out = []
    server = await serve_grpc(PORT)
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{PORT}") as ch:
            stub = nlp_pb2_grpc.NlpServiceStub(ch)

            b = await stub.GetSentimentBatch(nlp_pb2.SentimentBatchRequest(
                texts=["I love this, amazing!", "This is terrible and awful", "the meeting is at 3pm"]
            ))
            sentiments = [r.sentiment for r in b.results]
            assert sentiments == ["positive", "negative", "neutral"], sentiments
            out.append(f"GetSentimentBatch -> {sentiments}")

            e = await stub.GetEntitiesForMention(nlp_pb2.EntitiesRequest(
                text="Acme Corporation released a new product in London."
            ))
            out.append(f"GetEntitiesForMention -> {len(e.entities)} entities: {[en.text for en in e.entities][:3]}")
    finally:
        await server.stop(grace=1)

    print("\n".join("PASS  " + s for s in out))
    print("\nNLP gRPC CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
