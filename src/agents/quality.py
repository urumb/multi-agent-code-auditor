# Author: urumb
from .base import AnalysisAgent


class QualityAgent(AnalysisAgent):
    category = "quality"
    label = "Quality Agent"
    temperature = 0.2
    role = (
        "You are a Senior Code Quality Engineer. Analyze the code for maintainability, "
        "correctness risks, brittle abstractions, poor error handling, duplicated logic, "
        "unclear boundaries, and testability issues. Do not report security vulnerabilities or "
        "performance problems: other agents cover those."
    )
    explanation_hint = "why this harms correctness or maintainability"
