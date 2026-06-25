# Author: urumb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..findings import normalize_findings
from ..state import AuditorState

class SecurityAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.MODEL_NAME,
            temperature=0.1
        )
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

If there are no findings, return {{"findings": []}}."""),
            ("user", "Code Snippet:\n{code}")
        ])

    def run(self, state: AuditorState) -> AuditorState:
        print("--- Security Agent: Scanning for Vulnerabilities ---")
        snippets = state.get("code_snippets", [])
        results = []

        chain = self.prompt | self.llm

        for i, snippet in enumerate(snippets):
            try:
                response = chain.invoke({"code": snippet})
                results.append({
                    "snippet_index": i,
                    "analysis": response.content,
                    "findings": normalize_findings(response.content, "security", snippet),
                })
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e),
                    "findings": [],
                })

        return {"security_analysis": results}
