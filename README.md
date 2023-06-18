# AI Customer Support Copilot

A backend service that answers customer support questions using an LLM.
It classifies each message into a fixed intent taxonomy, builds a structured
prompt with conversation history, and returns a concise customer-friendly response.

Personal learning project. Built May–June 2023.
Full design doc: `docs/architecture.md`

## Stack

Python, FastAPI, Pydantic, PostgreSQL, Docker, pytest.
LLM calls are mocked in Phase 1 so the API runs without an API key.

## Quickstart

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

With Docker (includes PostgreSQL):

```bash
docker compose up --build
```

## API examples

```bash
curl -X POST localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": "C10291", "message": "I was charged twice for my order."}'

curl localhost:8000/api/v1/conversations/conv-abcdef12

curl localhost:8000/api/v1/health
curl localhost:8000/api/v1/metrics
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | empty | LLM provider key (Phase 2) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name (Phase 2) |
| `DATABASE_URL` | empty | Postgres URL (Phase 2 persistence) |
| `API_KEY` | `dev-key-change-me` | Placeholder for API auth |
| `HISTORY_WINDOW` | `10` | Messages included in prompt context |
| `LLM_TIMEOUT_S` | `10` | Per-call LLM timeout |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per customer per minute |
| `LOG_LEVEL` | `INFO` | Log verbosity: DEBUG, INFO, WARNING, ERROR |

## Observability

Logs are single-line JSON on stdout. Every request carries a `request_id`
(shared by the access log and the chat log), and customer IDs are SHA-256
hashed before logging so log storage never holds PII.

```bash
docker compose up --build 2>&1 | grep '"path": "/api/v1/chat"'
```

`/api/v1/metrics` exposes request counts, error rate, p50/p95 latency,
LLM call counts and errors, and total prompt/completion tokens.
In-memory counters reset on restart; the `model_requests` table in
PostgreSQL is the durable source of truth for token and latency history.

Suggested alert thresholds (wire to your monitor of choice):
p95 latency above 3s, error rate above 2%, LLM error burst.

## Testing

```bash
pytest -q
```

## Evaluation

```bash
uvicorn app.main:app --port 8000
python evaluation/evaluate.py
```

Measures intent accuracy and p95 latency over the question set in
`evaluation/questions.json`. Numbers are targets until measured on a real run.

## Project phases

- Phase 0: scaffold, health endpoint, config from env (done)
- Phase 1: chat API with mocked LLM, validation, request IDs, idempotency (done)
- Phase 2: real LLM calls, PostgreSQL persistence, token logging (done)
  - `OPENAI_API_KEY` set: real intent + response calls (timeout, one retry,
    strict label parsing, secret-output scanning). Without a key the API uses
    the Phase 1 mocks. `DATABASE_URL` set: Postgres persistence, else in-memory.
  - Full stack: `docker compose up --build` with `OPENAI_API_KEY` in `.env`
- Phase 3: structured logging, metrics, alerting thresholds (done: JSON log lines with request_id correlation, hashed customer IDs, per-stage LLM logs, extended /metrics with token counts; retries, fallback, and rate limiting were already in place from Phases 1-2). 15 tests passing.
- Phase 4: eval runs with recorded numbers (not started)

## Notes

- All customer IDs and messages in this repo are synthetic. No real PII.
- `app/prompts/` holds the prompt templates used in Phase 2.
- See `docs/architecture.md` for requirements, diagrams, and API contracts.
