# Author: urumb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..state import AuditorState
import json

class SecurityAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.MODEL_NAME,
            temperature=0.1
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Security Engineer. Analyze the provided code snippet for security vulnerabilities (OWASP Top 10, SQLi, XSS, hardcoded secrets, etc.). Return a JSON object with a list of 'issues' (severity, description, line_number_hint). If no issues, return empty list."),
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
                # Attempt to parse specific JSON or just store text
                # For robustness, we'll store the raw content for now, 
                # but ideally we'd force structured output.
                results.append({
                    "snippet_index": i,
                    "analysis": response.content
                })
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e)
                })

        return {"security_analysis": results}
