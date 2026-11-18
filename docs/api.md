# API

`GET /health` returns process health and mode. `GET /docs` opens OpenAPI documentation.

```bash
curl http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: demo-acme' \
  -d '{"question":"Atlas E101 如何排查","session_id":"demo-session"}'
```

Response: `answer`, `sources`, `context`, `status`, `mode`, `session_id`, and `metrics` (latency, context characters, number of history turns).

```bash
curl http://localhost:8000/api/ticket \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: demo-acme' \
  -d '{"question":"生成工单","session_id":"demo-session"}'
```

Ticket uses the latest stored turn for that tenant and session. It is returned as a draft and not submitted anywhere. The `question` field is required by the shared request schema but is not used to compose the ticket.
