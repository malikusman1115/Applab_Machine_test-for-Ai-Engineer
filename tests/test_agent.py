import pytest

from agentic_qa.agent import AgenticQA
from agentic_qa.models import QARequest, Source, ToolName, ToolResult
from agentic_qa.planner import Planner
from agentic_qa.tools import Tool, ToolRegistry


class FakeWebTool(Tool):
    name = ToolName.web_search
    input_model = __import__("agentic_qa.models", fromlist=["WebSearchInput"]).WebSearchInput
    output_model = __import__("agentic_qa.models", fromlist=["WebSearchOutput"]).WebSearchOutput

    async def _run_validated(self, payload):
        return ToolResult(
            tool=self.name,
            success=True,
            data={
                "query": payload.query,
                "results": [{"title": "Example", "url": "https://example.com", "snippet": "Example grounded result."}],
            },
            sources=[Source(name="Example", url="https://example.com")],
        )


class FakeWeatherTool(Tool):
    name = ToolName.weather
    input_model = __import__("agentic_qa.models", fromlist=["WeatherInput"]).WeatherInput
    output_model = __import__("agentic_qa.models", fromlist=["WeatherOutput"]).WeatherOutput

    async def _run_validated(self, payload):
        return ToolResult(
            tool=self.name,
            success=True,
            data={
                "location": payload.location,
                "condition": "clear",
                "temperature_c": 27.5,
                "humidity_percent": 50,
                "wind_kph": 10.0,
                "source": {"name": "Dummy Weather Tool", "url": "tool://dummy-weather"},
            },
            sources=[Source(name="Dummy Weather Tool", url="tool://dummy-weather")],
        )


@pytest.mark.asyncio
async def test_agent_returns_structured_grounded_answer():
    registry = ToolRegistry([FakeWebTool(), FakeWeatherTool()])
    response = await AgenticQA(registry=registry, planner=Planner()).answer(QARequest(question="What is the weather in Lahore today?"))
    assert response.answer
    assert response.sources
    assert response.latency_ms.total >= 0
    assert response.tokens.prompt == 0
    assert any(source.url == "https://example.com" for source in response.sources)
