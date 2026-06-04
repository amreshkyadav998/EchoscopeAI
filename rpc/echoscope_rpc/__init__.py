"""echoscope_rpc — shared gRPC contracts (generated stubs) + client helpers.

Servers: Analytics (:50051), NLP (:50052).
Clients: Report/Notification → Analytics; Report/Analytics → NLP.
"""

from . import analytics_pb2, analytics_pb2_grpc, nlp_pb2, nlp_pb2_grpc
from .client import channel, grpc_status_to_http, with_retry

__all__ = [
    "analytics_pb2",
    "analytics_pb2_grpc",
    "nlp_pb2",
    "nlp_pb2_grpc",
    "channel",
    "with_retry",
    "grpc_status_to_http",
]
