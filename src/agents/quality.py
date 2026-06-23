# Author: urumb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from ..config import Config
from ..findings import normalize_findings
from ..state import AuditorState


class QualityAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.MODEL_NAME,
            temperature=0.2
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior Code Quality Engineer. Analyze the code for maintainability, correctness risks, brittle abstractions, poor error handling, duplicated logic, unclear boundaries, and testability issues.

Return only valid JSON with this exact shape:
{
  "findings": [
    {
      "severity": "Critical|High|Medium|Low",
      "issue": "short actionable title",
      "explanation": "why this harms correctness or maintainability",
      "suggested_fix": "specific developer guidance",
      "before_code": "relevant problematic code",
      "after_code": "improved replacement code",
      "cwe": ""
    }
  ]
}

If there are no findings, return {"findings": []}."""),
            ("user", "Code Snippet:\n{code}")
        ])

    def run(self, state: AuditorState) -> AuditorState:
        print("--- Quality Agent: Reviewing Maintainability ---")
        snippets = state.get("code_snippets", [])
        results = []

        chain = self.prompt | self.llm

        for i, snippet in enumerate(snippets):
            try:
                response = chain.invoke({"code": snippet})
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
