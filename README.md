# Agentic QA Service

A production-minded Python 3.10+ take-home implementation for an Agentic QA service that plans tool calls, executes live and dummy tools, validates structured I/O, and returns grounded JSON answers with citations and latency metrics.

## Features

- Deterministic planner with a visible core agent loop
- Tool registry with JSON schemas for inputs and outputs
- DuckDuckGo instant-answer web search tool
- Dummy weather tool
- Pydantic validation for requests, tool calls, tool outputs, and final responses
- Structured final output with `answer`, `sources`, `latency_ms`, and `tokens`
- Retry handling, HTTP timeout, TTL caching, and concurrency limits
- JSON stdout tracing for planner, tools, cache hits, and answer completion
- FastAPI endpoints, CLI runner, Dockerfile, tests, and `.env.example`
- Simple policy layer blocking network calls outside allowed domains
- Streaming endpoint for bonus coverage

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn agentic_qa.api:app --reload --app-dir app
```

## CLI

```bash
PYTHONPATH=app python -m agentic_qa.cli "What is the weather in Lahore today?"
```

## API

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the weather in Lahore today?","max_sources":5}'
```

## Response shape

```json
{
  "answer": "string",
  "sources": [{"name": "string", "url": "string"}],
  "latency_ms": {"total": 123, "by_step": {"plan": 1, "tools": 45, "synthesize": 1}},
  "tokens": {"prompt": 0, "completion": 0}
}
```

## Endpoints

- `GET /health`
- `GET /tools`
- `POST /answer`
- `POST /answer/stream`

## Tests

```bash
pytest
```

## Docker

```bash
docker build -t agentic-qa-service .
docker run --rm -p 8000:8000 agentic-qa-service
```

