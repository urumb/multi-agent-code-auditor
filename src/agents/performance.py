# Author: urumb
from .base import AnalysisAgent


class PerformanceAgent(AnalysisAgent):
    category = "performance"
    label = "Performance Agent"
    temperature = 0.2
    role = (
        "You are a Senior Performance Engineer. Analyze the code for inefficient algorithms, "
        "unnecessary repeated work, avoidable I/O, memory pressure, blocking operations, and "
        "scalability risks."
    )
    explanation_hint = "why this affects runtime, memory, or scalability"
    after_hint = "optimized replacement code"
