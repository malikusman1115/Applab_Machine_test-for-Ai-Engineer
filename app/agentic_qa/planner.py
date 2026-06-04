from __future__ import annotations

import re

from .models import ToolCall, ToolName


class Planner:
    weather_terms = re.compile(r"\b(weather|temperature|forecast|rain|humidity|wind)\b", re.I)
    current_terms = re.compile(r"\b(who|what|when|where|why|how|latest|current|today|news|search|web|lookup|find)\b", re.I)
    location_pattern = re.compile(r"\b(?:in|for|at)\s+([A-Za-z][A-Za-z\s,.-]{1,80})", re.I)

    def plan(self, question: str, max_sources: int = 5) -> list[ToolCall]:
        calls: list[ToolCall] = []
        if self.weather_terms.search(question):
            calls.append(ToolCall(tool=ToolName.weather, arguments={"location": self._location(question)}))
        if self.current_terms.search(question) or not calls:
            calls.append(ToolCall(tool=ToolName.web_search, arguments={"query": question, "max_results": max_sources}))
        return calls

    def _location(self, question: str) -> str:
        match = self.location_pattern.search(question)
        if match:
            return match.group(1).strip(" ?.!,")
        return "Karachi, Pakistan"
