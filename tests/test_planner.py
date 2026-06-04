from agentic_qa.models import ToolName
from agentic_qa.planner import Planner


def test_weather_question_uses_weather_and_web():
    calls = Planner().plan("What is the weather in Lahore today?", 3)
    assert [call.tool for call in calls] == [ToolName.weather, ToolName.web_search]
    assert calls[0].arguments["location"] == "Lahore today"


def test_general_question_uses_web():
    calls = Planner().plan("Who founded OpenAI?", 3)
    assert len(calls) == 1
    assert calls[0].tool == ToolName.web_search
