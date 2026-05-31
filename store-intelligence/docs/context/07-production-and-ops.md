# Production Readiness (Part C)

> Part of [Project Context Index](./README.md)

---

## 9. Production Readiness Requirements (Part C)

### 9.1 Docker

- `docker compose up` starts API + DB — **no manual steps** beyond `git clone`
- Mount `data/` volume for POS + events
- Expose port 8000
- Healthcheck hitting `/health`

### 9.2 Structured Logging (required fields)

Every request logs: `trace_id`, `store_id`, `endpoint`, `latency_ms`, `event_count` (ingest only), `status_code`. See [Appendix C](#appendix-c-structured-log-format).

### 9.3 Idempotency

- `POST /events/ingest` safe to call twice with identical payload
- Test must verify no duplicate rows in DB

### 9.4 Graceful Degradation

- Database unavailable → HTTP **503** with `{ "status": "UNAVAILABLE", "reason": "..." }`
- **Never** return raw Python stack traces to client

### 9.5 Testing

- Statement coverage **>70%** (`pytest --cov=app`)
- Mandatory edge cases: empty store, all-staff clip, zero purchases, re-entry in funnel (Section 17)

### 9.6 README

- Complete setup in **≤5 commands** (Section 22)
- How to run detection pipeline against clips
- Where event output goes and how to ingest into API

---
