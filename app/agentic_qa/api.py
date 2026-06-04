from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .agent import AgenticQA
from .models import QARequest, QAResponse

app = FastAPI(title="Agentic QA Service", version="1.0.0")
agent = AgenticQA()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
async def tools() -> dict:
    return agent.registry.schemas()


@app.post("/answer", response_model=QAResponse)
async def answer(request: QARequest) -> QAResponse:
    return await agent.answer(request)


@app.post("/answer/stream")
async def answer_stream(request: QARequest) -> StreamingResponse:
    async def stream():
        response = await agent.answer(request)
        for token in response.answer.split():
            yield token + " "
        yield "\n" + response.model_dump_json()
    return StreamingResponse(stream(), media_type="text/plain")
