from __future__ import annotations

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError
from .cache import TTLCache
from .config import settings
from .logging import emit
from .models import Source, ToolName, ToolResult, WeatherInput, WeatherOutput, WebSearchInput, WebSearchItem, WebSearchOutput
from .policy import NetworkPolicy


class Tool(ABC):
    name: ToolName
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def __init__(self, cache: TTLCache[dict[str, Any]] | None = None) -> None:
        self.cache = cache or TTLCache(ttl_seconds=settings.cache_ttl_seconds)

    @abstractmethod
    async def _run_validated(self, payload: BaseModel) -> ToolResult:
        raise NotImplementedError

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        try:
            payload = self.input_model.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult(tool=self.name, success=False, error=exc.errors()[0]["msg"], latency_ms=0)
        key = self._cache_key(payload)
        cached = self.cache.get(key)
        if cached is not None:
            result = ToolResult.model_validate(cached)
            result.latency_ms = int((time.perf_counter() - started) * 1000)
            emit("tool_cache_hit", tool=self.name.value, latency_ms=result.latency_ms)
            return result
        result = await self._run_validated(payload)
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        if result.success:
            self.cache.set(key, result.model_dump())
        emit("tool_completed", tool=self.name.value, success=result.success, latency_ms=result.latency_ms)
        return result

    def _cache_key(self, payload: BaseModel) -> str:
        raw = payload.model_dump_json()
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{self.name.value}:{digest}"


class WebSearchTool(Tool):
    name = ToolName.web_search
    input_model = WebSearchInput
    output_model = WebSearchOutput

    def __init__(self, client: httpx.AsyncClient | None = None, cache: TTLCache[dict[str, Any]] | None = None) -> None:
        super().__init__(cache=cache)
        self.client = client
        self.policy = NetworkPolicy()

    async def _run_validated(self, payload: WebSearchInput) -> ToolResult:
        url = "https://api.duckduckgo.com/"
        self.policy.validate_url(url)
        params = {"q": payload.query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        try:
            data = await self._request(url, params)
            output = self._parse(payload.query, data, payload.max_results)
            return ToolResult(
                tool=self.name,
                success=True,
                data=output.model_dump(),
                sources=[Source(name=item.title, url=item.url) for item in output.results],
            )
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))

    async def _request(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(settings.retry_attempts + 1):
            client = self.client or httpx.AsyncClient(timeout=settings.request_timeout_seconds)
            close = self.client is None
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= settings.retry_attempts:
                    raise
                await asyncio.sleep(min(2.0, 0.2 * (2**attempt)))
            finally:
                if close:
                    await client.aclose()
        if last_error is not None:
            raise last_error
        raise RuntimeError("HTTP request failed")

    def _parse(self, query: str, data: dict[str, Any], max_results: int) -> WebSearchOutput:
        items: list[WebSearchItem] = []
        abstract_url = data.get("AbstractURL")
        abstract_text = data.get("AbstractText")
        heading = data.get("Heading") or query
        if abstract_url and abstract_text:
            items.append(WebSearchItem(title=heading, url=abstract_url, snippet=abstract_text))
        for topic in data.get("RelatedTopics", []):
            items.extend(self._extract_topic(topic))
            if len(items) >= max_results:
                break
        deduped: list[WebSearchItem] = []
        seen: set[str] = set()
        for item in items:
            if item.url and item.url not in seen:
                seen.add(item.url)
                deduped.append(item)
            if len(deduped) >= max_results:
                break
        if not deduped:
            fallback_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
            deduped.append(WebSearchItem(title=f"DuckDuckGo search for {query}", url=fallback_url, snippet="No instant-answer result was available."))
        return WebSearchOutput(query=query, results=deduped)

    def _extract_topic(self, topic: dict[str, Any]) -> list[WebSearchItem]:
        if "Topics" in topic:
            return [item for child in topic.get("Topics", []) for item in self._extract_topic(child)]
        first_url = topic.get("FirstURL")
        text = topic.get("Text")
        if not first_url or not text:
            return []
        title = text.split(" - ", 1)[0][:120]
        return [WebSearchItem(title=title, url=first_url, snippet=text)]


class WeatherTool(Tool):
    name = ToolName.weather
    input_model = WeatherInput
    output_model = WeatherOutput

    async def _run_validated(self, payload: WeatherInput) -> ToolResult:
        signature = int(hashlib.sha256(payload.location.lower().encode("utf-8")).hexdigest(), 16)
        conditions = ["clear", "partly cloudy", "cloudy", "light rain", "windy"]
        output = WeatherOutput(
            location=payload.location,
            condition=conditions[signature % len(conditions)],
            temperature_c=round(12 + (signature % 2300) / 100, 1),
            humidity_percent=35 + signature % 55,
            wind_kph=round(3 + signature % 280 / 10, 1),
            source=Source(name="Dummy Weather Tool", url="tool://dummy-weather"),
        )
        await asyncio.sleep(0)
        return ToolResult(tool=self.name, success=True, data=output.model_dump(), sources=[output.source])


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: ToolName) -> Tool:
        return self._tools[name]

    def schemas(self) -> dict[str, dict[str, Any]]:
        return {
            name.value: {
                "input_schema": tool.input_model.model_json_schema(),
                "output_schema": tool.output_model.model_json_schema(),
            }
            for name, tool in self._tools.items()
        }


def default_registry() -> ToolRegistry:
    shared_cache: TTLCache[dict[str, Any]] = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
    return ToolRegistry([WebSearchTool(cache=shared_cache), WeatherTool(cache=shared_cache)])
