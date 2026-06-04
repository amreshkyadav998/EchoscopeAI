"""NLP gRPC server (HLD §9/§12).

RPCs: GetSentimentBatch (bulk sentiment for reports), GetEntitiesForMention.
Runs on an internal-only port alongside FastAPI.
"""

from __future__ import annotations

import grpc
from loguru import logger as log

from app.analysis import analyze_text
from config import get_settings
from echoscope_rpc import nlp_pb2, nlp_pb2_grpc


class NlpServicer(nlp_pb2_grpc.NlpServiceServicer):
    async def GetSentimentBatch(self, request, context):
        settings = get_settings()
        results = []
        for text in request.texts:
            r = analyze_text(text, settings)
            results.append(
                nlp_pb2.SentimentResult(sentiment=r.sentiment, confidence=r.confidence, keywords=r.keywords)
            )
        return nlp_pb2.SentimentBatchResponse(results=results)

    async def GetEntitiesForMention(self, request, context):
        r = analyze_text(request.text, get_settings())
        ents = [
            nlp_pb2.Entity(text=e["text"], label=e["label"], score=float(e.get("score", 0.0)))
            for e in r.entities
        ]
        return nlp_pb2.EntitiesResponse(entities=ents)


async def serve_grpc(port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    nlp_pb2_grpc.add_NlpServiceServicer_to_server(NlpServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    log.info("nlp gRPC server started", port=port)
    return server
