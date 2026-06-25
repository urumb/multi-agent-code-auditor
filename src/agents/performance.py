# Author: urumb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..findings import normalize_findings
from ..state import AuditorState

class PerformanceAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.MODEL_NAME,
            temperature=0.2
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior Performance Engineer. Analyze the code for inefficient algorithms, unnecessary repeated work, avoidable I/O, memory pressure, blocking operations, and scalability risks.

Return only valid JSON with this exact shape:
{{
  "findings": [
    {{
      "severity": "Critical|High|Medium|Low",
      "issue": "short actionable title",
      "explanation": "why this affects runtime, memory, or scalability",
      "suggested_fix": "specific developer guidance",
      "before_code": "relevant inefficient code",
      "after_code": "optimized replacement code",
      "cwe": ""
    }}
  ]
}}

If there are no findings, return {{"findings": []}}."""),
            ("user", "Code Snippet:\n{code}")
        ])

    def run(self, state: AuditorState) -> AuditorState:
        print("--- Performance Agent: Analyzing Complexity ---")
        snippets = state.get("code_snippets", [])
        results = []

        chain = self.prompt | self.llm

        for i, snippet in enumerate(snippets):
            try:
                response = chain.invoke({"code": snippet})
                results.append({
                    "snippet_index": i,
                    "analysis": response.content,
                    "findings": normalize_findings(response.content, "performance", snippet),
                })
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e),
                    "findings": [],
                })

        return {"performance_analysis": results}
