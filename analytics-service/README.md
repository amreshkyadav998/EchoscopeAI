# Analytics Service (:8004)

Kafka consumer on `sentiment-processed`. Rolling aggregation (Pandas), sentiment trends,
Z-score spike detection, competitor scoring. 7 REST endpoints + gRPC server. Publishes
`analytics-updated` and `alert-triggered`.

_Implemented in Phase 8._
