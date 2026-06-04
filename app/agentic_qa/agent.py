from __future__ import annotations

import asyncio
import time
from collections import OrderedDict

from .config import settings
from .logging import emit
from .models import Latency, QARequest, QAResponse, Source, TokenUsage, ToolName, ToolResult, WebSearchOutput
from .planner import Planner
from .tools import ToolRegistry, default_registry


class AgenticQA:
    def __init__(self, registry: ToolRegistry | None = None, planner: Planner | None = None) -> None:
        self.registry = registry or default_registry()
        self.planner = planner or Planner()
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_tools)

    async def answer(self, request: QARequest) -> QAResponse:
        started = time.perf_counter()
        by_step: dict[str, int] = {}
        plan_started = time.perf_counter()
        calls = self.planner.plan(request.question, request.max_sources)
        by_step["plan"] = self._elapsed(plan_started)
        emit("plan_created", question=request.question, calls=[call.model_dump() for call in calls])
        tool_started = time.perf_counter()
        results = await asyncio.gather(*(self._run_tool(call.tool, call.arguments) for call in calls))
        by_step["tools"] = self._elapsed(tool_started)
        synth_started = time.perf_counter()
        answer, sources = self._synthesize(request.question, results)
        by_step["synthesize"] = self._elapsed(synth_started)
        total = self._elapsed(started)
        by_step.update({f"tool_{result.tool.value}": result.latency_ms for result in results})
        response = QAResponse(answer=answer, sources=sources, latency_ms=Latency(total=total, by_step=by_step), tokens=TokenUsage())
        emit("answer_completed", total_latency_ms=total, source_count=len(sources))
        return response

    async def _run_tool(self, name: ToolName, arguments: dict) -> ToolResult:
        async with self.semaphore:
            return await self.registry.get(name).run(arguments)

    def _synthesize(self, question: str, results: list[ToolResult]) -> tuple[str, list[Source]]:
        used = [result.tool.value for result in results if result.success]
        failed = [f"{result.tool.value}: {result.error}" for result in results if not result.success]
        source_map: OrderedDict[str, Source] = OrderedDict()
        parts: list[str] = []
        weather = next((result for result in results if result.tool == ToolName.weather and result.success), None)
        web = next((result for result in results if result.tool == ToolName.web_search and result.success), None)
        if weather:
            data = weather.data
            parts.append(
                f"The dummy weather tool reports {data['condition']} conditions in {data['location']}, "
                f"with {data['temperature_c']}°C, {data['humidity_percent']}% humidity, and {data['wind_kph']} kph wind."
            )
            for source in weather.sources:
                source_map[source.url] = source
        if web:
            output = WebSearchOutput.model_validate(web.data)
            if output.results:
                summaries = [f"{item.title}: {item.snippet}" for item in output.results[:3] if item.snippet]
                if summaries:
                    parts.append("Web search found: " + " ".join(summaries))
                else:
                    parts.append("Web search returned relevant source links, but limited instant-answer text was available.")
                for item in output.results:
                    source_map[item.url] = Source(name=item.title, url=item.url)
        if not parts:
            parts.append("I could not retrieve enough grounded information to answer the question confidently.")
        if used:
            parts.append(f"Tools used: {', '.join(used)}.")
        if failed:
            parts.append(f"Some tool calls failed: {'; '.join(failed)}.")
        parts.append(f"Question answered: {question}")
        return " ".join(parts), list(source_map.values())

    def _elapsed(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
