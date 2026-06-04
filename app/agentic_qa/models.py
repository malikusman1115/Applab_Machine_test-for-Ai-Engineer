from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ToolName(str, Enum):
    web_search = "web_search"
    weather = "weather"


class Source(BaseModel):
    name: str
    url: str


class Latency(BaseModel):
    total: int = 0
    by_step: dict[str, int] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    max_sources: int = Field(default=5, ge=1, le=10)


class QAResponse(BaseModel):
    answer: str
    sources: list[Source]
    latency_ms: Latency
    tokens: TokenUsage = Field(default_factory=TokenUsage)


class ToolCall(BaseModel):
    tool: ToolName
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    tool: ToolName
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)


class WeatherInput(BaseModel):
    location: str = Field(min_length=1, max_length=120)


class WebSearchItem(BaseModel):
    title: str
    url: str
    snippet: str = ""


class WebSearchOutput(BaseModel):
    query: str
    results: list[WebSearchItem]


class WeatherOutput(BaseModel):
    location: str
    condition: str
    temperature_c: float
    humidity_percent: int
    wind_kph: float
    source: Source
