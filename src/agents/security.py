# Author: urumb
from .base import AnalysisAgent


class SecurityAgent(AnalysisAgent):
    category = "security"
    label = "Security Agent"
    temperature = 0.1
    role = (
        "You are a Senior Security Engineer. Analyze the provided code snippet for security "
        "vulnerabilities including OWASP Top 10, SQL injection, XSS, unsafe deserialization, "
        "path traversal, auth bypasses, and hardcoded secrets."
    )
    explanation_hint = "why this is risky in this code"
    after_hint = "safer replacement code"
    cwe_hint = "CWE identifier, or empty string if unsure"
