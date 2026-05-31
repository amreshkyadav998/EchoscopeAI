# Notification Service (:8005)

WebSocket endpoints (`/ws/dashboard`, `/ws/alerts`) bridged via Redis Pub/Sub. Alert rule
evaluation engine with debounce, SendGrid email, alert history. Consumes `alert-triggered`
and `report-generated`.

_Implemented in Phases 9-10._
