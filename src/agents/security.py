# Author: urumb
import logging
from langchain_ollama import ChatOllama
from ..llm import make_llm, invoke_llm, AuditCancelled, ANALYSIS_MAX_TOKENS
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..findings import normalize_findings
from ..state import AuditorState

logger = logging.getLogger(__name__)

class SecurityAgent:
    def __init__(self):
        self._llm_cache: dict[str, ChatOllama] = {}
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior Security Engineer. Analyze the provided code snippet for security vulnerabilities including OWASP Top 10, SQL injection, XSS, unsafe deserialization, path traversal, auth bypasses, and hardcoded secrets.

Return only valid JSON with this exact shape:
{{
  "findings": [
    {{
      "severity": "Critical|High|Medium|Low",
      "issue": "short actionable title",
      "explanation": "why this is risky in this code",
      "suggested_fix": "specific developer guidance",
      "before_code": "relevant vulnerable code",
      "after_code": "safer replacement code",
      "cwe": "CWE identifier or empty string"
    }}
  ]
}}

Report at most 2 findings, most severe first. Keep issue under 8 words, explanation and suggested_fix under 25 words each, before_code and after_code to 1-2 lines each, and set cwe to "" if unsure.

If there are no findings, return {{"findings": []}}."""),
            ("user", "Code Snippet:\n{code}")
        ])

    def _get_llm(self) -> ChatOllama:
        """Build (and cache) the Ollama client for the currently configured model.

        Reads Config.MODEL_NAME on every call instead of capturing it once at
        construction time, so changing the model in Settings takes effect
        without restarting the backend.
        """
        model = Config.MODEL_NAME
        if model not in self._llm_cache:
            self._llm_cache[model] = make_llm(0.1, max_tokens=ANALYSIS_MAX_TOKENS)
        return self._llm_cache[model]

    def run(self, state: AuditorState) -> AuditorState:
        logger.info("Security Agent: scanning for vulnerabilities")
        snippets = state.get("code_snippets", [])
        results = []

        chain = self.prompt | self._get_llm()

        for i, snippet in enumerate(snippets):
            try:
                response = invoke_llm(chain, {"code": snippet}, state.get("cancel_event"))
                results.append({
                    "snippet_index": i,
                    "analysis": response.content,
                    "findings": normalize_findings(response.content, "security", snippet),
                })
            except AuditCancelled:
                raise
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e),
                    "findings": [],
                })

        return {"security_analysis": results}
