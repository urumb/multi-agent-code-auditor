# Author: urumb
"""Shared implementation of the three snippet-analysis agents.

Security, Performance and Quality differ only in their role description,
temperature and the key they write to; everything else (prompt shape,
static-analysis hints, the per-snippet loop, cancellation, error handling)
lives here so it can't drift between them.
"""
import logging
from typing import Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from ..config import Config
from ..findings import normalize_findings
from ..llm import AuditCancelled, invoke_llm, make_llm
from ..state import AuditorState
from ..static_analysis import hints_for_chunk

logger = logging.getLogger(__name__)

# Output tokens: a fixed overhead plus a budget per requested finding.
_TOKENS_BASE = 60
_TOKENS_PER_FINDING = 130

_RESPONSE_FORMAT = """
Return only valid JSON with this exact shape:
{{{{
  "findings": [
    {{{{
      "severity": "Critical|High|Medium|Low",
      "issue": "short actionable title",
      "explanation": "{explanation_hint}",
      "suggested_fix": "specific developer guidance",
      "before_code": "the exact problematic line copied from the snippet",
      "after_code": "{after_hint}",
      "cwe": "{cwe_hint}"
    }}}}
  ]
}}}}

Only report problems you are confident are real in THIS code and that belong to your specialty. Most code has few or no such problems: returning an empty list is the correct answer when you find none, so never pad the list.

Report at most {{max_findings}} findings, most severe first. Keep issue under 8 words, explanation and suggested_fix under 25 words each, before_code and after_code to 1-2 lines each. Copy before_code exactly from the snippet so it can be located.

Static analysis tools already reported the issues listed by the user. Do NOT repeat them; look for other problems they missed.

If there are no findings, return {{{{"findings": []}}}}."""


def analysis_max_tokens() -> int:
    return _TOKENS_BASE + _TOKENS_PER_FINDING * Config.MAX_FINDINGS_PER_CHUNK


class AnalysisAgent:
    #: Category key used in findings ("security", "performance", "quality").
    category: str = ""
    #: Human-readable name for logs.
    label: str = ""
    temperature: float = 0.1
    role: str = ""
    explanation_hint: str = ""
    after_hint: str = "improved replacement code"
    cwe_hint: str = ""

    def __init__(self):
        self._llm_cache: Dict[tuple, ChatOllama] = {}
        system = self.role + "\n" + _RESPONSE_FORMAT.format(
            explanation_hint=self.explanation_hint,
            after_hint=self.after_hint,
            cwe_hint=self.cwe_hint,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("user", "Already reported by static analysis:\n{hints}\n\nCode Snippet:\n{code}"),
        ])

    def _get_llm(self) -> ChatOllama:
        """Build (and cache) the Ollama client for the current model.

        Reads Config on every call so changing the model in Settings takes
        effect without restarting the backend.
        """
        key = (Config.MODEL_NAME, analysis_max_tokens())
        if key not in self._llm_cache:
            self._llm_cache[key] = make_llm(self.temperature, max_tokens=key[1])
        return self._llm_cache[key]

    def run(self, state: AuditorState) -> AuditorState:
        logger.info("%s: analyzing %d snippet(s)", self.label, len(state.get("code_snippets", [])))
        snippets = state.get("code_snippets", [])
        static_findings = state.get("static_findings", [])
        results = []

        chain = self.prompt | self._get_llm()

        for i, snippet in enumerate(snippets):
            try:
                response = invoke_llm(
                    chain,
                    {
                        "code": snippet,
                        "hints": hints_for_chunk(static_findings, snippet, self.category),
                        "max_findings": Config.MAX_FINDINGS_PER_CHUNK,
                    },
                    state.get("cancel_event"),
                )
                results.append({
                    "snippet_index": i,
                    "analysis": response.content,
                    "findings": normalize_findings(response.content, self.category, snippet),
                })
            except AuditCancelled:
                raise
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e),
                    "findings": [],
                })

        return {f"{self.category}_analysis": results}
