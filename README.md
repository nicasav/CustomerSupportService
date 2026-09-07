# Customer Support Service

Customer support and ticketing agent for the BGTS take-home assessment. The
runtime can use local Ollama with `qwen2.5:3b`; tests remain deterministic by
injecting the rule-based classifier or a mocked Ollama client.

## Run locally

```bash
git clone https://github.com/nicasav/CustomerSupportService.git
cd CustomerSupportService
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env.example` ships with `LLM_PROVIDER=ollama`. If you just want to run the
app without installing anything else, set `LLM_PROVIDER=deterministic` in
`.env` and skip straight to the "Start the API" step below — the rule-based
classifier requires no external model or service.

To use the shipped default (Ollama + local Qwen 2.5 3B) instead, install and
start Ollama first:

```bash
brew install ollama       # macOS shown; see https://ollama.com/download for other platforms
ollama serve
ollama pull qwen2.5:3b
```

Start the API:

```bash
python -m uvicorn app.main:app --reload
```

Using `python -m uvicorn` (rather than a bare `uvicorn`) ensures the
interpreter from the active virtual environment is used, avoiding a PATH
collision with any globally installed `uvicorn` (for example from a
Homebrew Python).

The service runs at `http://127.0.0.1:8000`. Swagger is available at
`http://127.0.0.1:8000/docs`.

Run tests with:

```bash
python -m pytest
```

## Environment

`.env.example` defines:

- `APP_NAME` — service name.
- `ENVIRONMENT` — deployment environment label.
- `LLM_PROVIDER` — `ollama` for local Qwen or `deterministic` for rule-based
  development.
- `LLM_MODEL` — Ollama model name; defaults to `qwen2.5:3b`.
- `LLM_BASE_URL` — Ollama API URL; defaults to `http://127.0.0.1:11434`.
- `LLM_FALLBACK_TO_DETERMINISTIC` — when `true`, use the deterministic
  classifier if Ollama is unavailable or returns invalid structured output.
- `CHECKPOINT_PATH` — SQLite file used by LangGraph checkpoints.

Never commit a real `.env` file or API keys.

## API examples

### Routine request

```bash
curl -X POST http://127.0.0.1:8000/requests \
  -H 'content-type: application/json' \
  -d '{"message":"Where is my ORD-10433 order?"}'
```

This returns a completed response with the order lookup and workflow steps.

### Human approval flow

Start a risky request:

```bash
curl -X POST http://127.0.0.1:8000/requests \
  -H 'content-type: application/json' \
  -d '{"message":"Refund my ORD-10432 today or I will take legal action."}'
```

The response contains `status: "pending_approval"` and a `reference`. Resume
that exact workflow later:

```bash
curl -X POST \
  http://127.0.0.1:8000/requests/<reference>/decision \
  -H 'content-type: application/json' \
  -d '{"approved":true,"note":"Approved by support"}'
```

Rejecting uses `"approved": false`. A second decision returns `409`; an
unknown reference returns `404`.

## Architecture

```text
api -> services -> orchestration -> domain/tools/repositories
```

- **API** contains FastAPI routes and boundary schemas only.
- **Services** translate HTTP operations into workflow operations.
- **Orchestration** owns LangGraph nodes, conditional routing, interrupts, and
  checkpoint configuration.
- **Domain** contains validated Pydantic models and the pure risk policy.
- **Tools/repositories** provide typed access to mock order data.

The risk policy requires approval for a legal threat, urgency `4+`, or a
refund above `500`. These rules are explicit and testable rather than hidden
inside a prompt.

SQLite checkpoints use the request reference as LangGraph `thread_id`. A
pending workflow can therefore be resumed after the process restarts, and
classification/order lookup are not repeated during resume.

## End-to-end request lifecycle

1. FastAPI validates the body with `RequestCreate`.
2. `TicketService.start()` creates a UUID reference and uses it as the
   LangGraph `thread_id`.
3. The classifier produces `ExtractedIntent`. Ollama uses
   `ExtractedIntent.model_json_schema()` through its `format` parameter;
   tests inject the deterministic classifier or a mocked HTTP client.
4. `OrderLookupTool` validates the order number and queries the repository.
5. `TrackingLookupTool` uses the order's tracking number to load shipment
   status from the same repository.
6. `assess_risk()` applies the legal-threat, urgency, and refund-value rules.
7. LangGraph creates a routine response or records pending state and calls
   `interrupt()`.
8. A later decision becomes `Command(resume=...)`, so LangGraph continues at
   the interrupt instead of rerunning classification or order lookup.
9. `TicketService` maps the final `WorkflowState` to `FinalResponse`.

Each transition appends a UTC-timestamped `WorkflowStep`, making the result
auditable and allowing tests to verify which nodes ran.

## Code guide

### Entry point and configuration

- `app/main.py`: `app` is the FastAPI application; `lifespan()` creates and
  closes the shared repository, classifier, graph, and SQLite saver.
- `app/core/config.py`: `Settings` defines environment-backed settings and
  `get_settings()` returns the cached settings instance.

### HTTP layer

- `app/api/schemas.py`: `RequestCreate`, `DecisionRequest`, `PendingResponse`,
  and `FinalResponse` are strict HTTP DTOs.
- `app/api/routes.py`: `health()` checks liveness, `create_request()` starts a
  workflow, and `decide_request()` resumes one while mapping errors to `404`
  and `409`.

### Domain layer

- `app/domain/models.py`: enums and Pydantic models define topics, urgency,
  orders, intent, risk, decisions, audit steps, and complete workflow state.
- `app/domain/risk_policy.py`: `assess_risk()` is a pure function with no
  network or persistence dependency.

### Data access and tools

- `app/repositories/orders.py`: `OrderRepository` is the protocol and
  `JsonOrderRepository` validates and indexes the mock JSON dataset.
- `app/tools/order_lookup.py`: `OrderLookupInput` validates tool arguments and
  `OrderLookupTool.run()` delegates to the repository.
- `app/tools/tracking_lookup.py`: `TrackingLookupInput` validates tracking
  arguments and `TrackingLookupTool.run()` returns shipment status. Both
  tools are injected into and called by the LangGraph workflow.

### Classifiers

- `app/services/classifier.py`: `IntentClassifier` is the replaceable
  contract; `OllamaIntentClassifier.classify()` sends schema-constrained JSON
  requests with the customer message wrapped in `<customer_message>`
  delimiters; `DeterministicIntentClassifier.classify()` is the offline rules
  implementation; `FallbackIntentClassifier` handles explicit Ollama failures;
  `looks_like_prompt_injection()` flags common override phrasing for audit
  logging.
- `app/services/prompts.py`: keeps the Ollama system prompt separate from
  classifier code and instructs the model to treat delimited customer text
  as untrusted data, never as instructions.

### Orchestration and services

- `app/orchestration/graph.py`: `build_support_graph()` wires classification,
  order lookup, shipment tracking, risk routing, routine response, and HITL
  pause. `_step()` creates audit records. `classify_node` appends a
  `security_flag` step when the message resembles a prompt-injection attempt.
  `WORKFLOW_RECURSION_LIMIT` is a defensive cap passed to every
  `graph.ainvoke()` call.
- `app/orchestration/checkpointer.py`: `sqlite_checkpointer()` initializes and
  manages the async SQLite saver.
- `app/services/ticket_service.py`: `TicketService.start()` starts a thread,
  `resume()` sends a human decision, and `_final_response()` maps internal
  state to the public response. The custom exceptions represent invalid and
  already-resolved references.

## Testing guide

Unit tests cover validation, classifiers, risk rules, and order lookup.
Integration tests cover graph branches, HITL interrupts, SQLite reopen
behavior, HTTP response bodies, and edge cases. Ollama tests use
`httpx.MockTransport`, so tests never call a real model. Malformed Ollama
output is surfaced as `OllamaClassificationError`; the configured fallback can
then preserve service availability without silently accepting invalid data.

```bash
python -m pytest -q
```

## Project structure

```text
app/
  api/             # HTTP routes and schemas
  core/            # Pydantic Settings configuration
  data/            # Mock orders and local SQLite checkpoint file
  domain/          # Pydantic models and pure business rules
  orchestration/   # LangGraph graph and checkpoint lifecycle
  repositories/    # Typed data access
  services/        # Application use cases
  tools/           # Typed workflow tools
tests/
  unit/            # Model, classifier, repository, and policy tests
  integration/     # Graph, persistence, and API tests
```

## Known limitations

- Response generation is still deterministic; Ollama is currently used for
  structured intent classification only.
- The Ollama model must be downloaded separately and is not included in Git.
- The mock data repository reads a small JSON file rather than a production
  database.
- The API process owns one SQLite saver lifecycle; production deployment
  would need operational database management and concurrency review.

## Security notes

- **Prompt injection**: the Ollama system prompt explicitly instructs the
  model to treat the customer message as untrusted data, not instructions,
  and the message is wrapped in `<customer_message>` delimiters before being
  sent. `looks_like_prompt_injection()` additionally flags common override
  phrasing (e.g. "ignore previous instructions") as a `security_flag` audit
  step for observability. This is defense-in-depth, not a hard guarantee:
  Ollama's `format` parameter already constrains model output to the
  `ExtractedIntent` schema, so an injected instruction cannot escape into
  arbitrary text or trigger unintended tool calls, but it could still skew
  which schema fields are extracted. The deterministic classifier is
  unaffected since it only does keyword matching.
- **Runaway execution / infinite loops**: `app/orchestration/graph.py` builds
  a strict directed acyclic graph — every edge points forward
  (`classify -> lookup_order -> lookup_tracking -> assess_risk ->
  {routine_response | mark_pending -> await_approval} -> END`) and no node
  can be revisited within one invocation, so it cannot loop indefinitely
  today. `WORKFLOW_RECURSION_LIMIT` is nonetheless passed to every
  `graph.ainvoke()` call in `TicketService` as a defensive guard, so that if
  a future change introduces a cycle (e.g. a re-classification retry),
  LangGraph raises `GraphRecursionError` instead of running forever.
