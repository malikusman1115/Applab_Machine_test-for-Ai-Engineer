import pytest

from agentic_qa.models import ToolName
from agentic_qa.tools import WeatherTool


@pytest.mark.asyncio
async def test_weather_tool_schema_and_output():
    result = await WeatherTool().run({"location": "Karachi"})
    assert result.success is True
    assert result.tool == ToolName.weather
    assert result.data["location"] == "Karachi"
    assert result.sources[0].url == "tool://dummy-weather"
