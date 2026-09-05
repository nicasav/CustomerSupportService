# Customer Support Service

Deterministic-first scaffold for the BGTS customer support and ticketing agent
technical assessment.

## Current scope

This first increment intentionally does not call an LLM. The project is being
built around a deterministic workflow so that validation, branching, and
human-in-the-loop persistence can be tested before an LLM adapter is added.

## Planned workflow

1. Validate and normalize the incoming customer message.
2. Extract a structured request (topic, urgency, order number, and risk flags).
3. Fetch order data through an order repository/tool abstraction.
4. Apply an explicit deterministic risk policy.
5. Return a routine response, or persist a pending approval reference.
6. Resume a pending workflow from its saved state after an approve/reject
   decision, without repeating extraction or tool calls.
7. Return the customer response and an auditable step summary.

## Project structure

```text
app/
  api/             # FastAPI routes and request/response schemas
  core/            # Configuration and shared application concerns
  data/            # Small mock order dataset
  domain/          # Pydantic domain models and enums
  orchestration/   # Stateful workflow and deterministic transitions
  repositories/    # Data access interfaces and in-memory implementations
  services/        # Application use cases
  tools/           # Typed tools exposed to the workflow
tests/
  unit/            # Isolated domain, repository, and policy tests
  integration/     # HTTP and pause/resume workflow tests
```

## Planned API

- `GET /health` — service and dependency health.
- `POST /requests` — start a customer request; returns either a final result
  or a pending approval reference.
- `POST /requests/{reference}/decision` — approve or reject a pending request
  and resume it from its saved state.

Implementation will be added incrementally on top of this scaffold.

## Development

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```
