# Author: urumb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..state import AuditorState

class PerformanceAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.MODEL_NAME,
            temperature=0.2
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Performance Engineer. Analyze the code for inefficiencies (Big-O complexity, memory leaks, redundant computations). Suggest optimizations."),
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
                    "analysis": response.content
                })
            except Exception as e:
                results.append({
                    "snippet_index": i,
                    "error": str(e)
                })

        return {"performance_analysis": results}
