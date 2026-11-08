# Author: urumb
from langchain_ollama import ChatOllama
from ..llm import make_llm, invoke_llm, ANALYSIS_MAX_TOKENS
from langchain_core.prompts import ChatPromptTemplate

from ..config import Config
from ..findings import normalize_findings
from ..state import AuditorState


class QualityAgent:
    def __init__(self):
        self._llm_cache: dict[str, ChatOllama] = {}
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior Code Quality Engineer. Analyze the code for maintainability, correctness risks, brittle abstractions, poor error handling, duplicated logic, unclear boundaries, and testability issues.

Return only valid JSON with this exact shape:
{{
  "findings": [
    {{
      "severity": "Critical|High|Medium|Low",
      "issue": "short actionable title",
      "explanation": "why this harms correctness or maintainability",
      "suggested_fix": "specific developer guidance",
      "before_code": "relevant problematic code",
      "after_code": "improved replacement code",
      "cwe": ""
    }}
  ]
}}

Report at most 2 findings, most severe first. Keep issue under 8 words, explanation and suggested_fix under 25 words each, before_code and after_code to 1-2 lines each, and set cwe to "" if unsure.

If there are no findings, return {{"findings": []}}."""),
            ("user", "Code Snippet:\n{code}")
        ])

    def _get_llm(self) -> ChatOllama:
        model = Config.MODEL_NAME
        if model not in self._llm_cache:
            self._llm_cache[model] = make_llm(0.2, max_tokens=ANALYSIS_MAX_TOKENS)
        return self._llm_cache[model]

    def run(self, state: AuditorState) -> AuditorState:
        print("--- Quality Agent: Reviewing Maintainability ---")
        snippets = state.get("code_snippets", [])
        results = []

        chain = self.prompt | self._get_llm()

        for i, snippet in enumerate(snippets):
            try:
                response = invoke_llm(chain, {"code": snippet})
                results.append({
                    "snippet_index": i,
                    "analysis": response.content,
                    "findings": normalize_findings(response.content, "quality", snippet),
                })
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e),
                    "findings": [],
                })

        return {"quality_analysis": results}
