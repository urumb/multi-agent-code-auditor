# Author: urumb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..state import AuditorState

class ReviewerAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.MODEL_NAME,
            temperature=0
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Lead Code Auditor. Synthesize the findings from the Security and Performance teams into a professional Markdown report.
            
            Structure:
            1. Executive Summary
            2. Security Vulnerabilities (High/Medium/Low)
            3. Performance Optimizations
            4. Detailed Code Recommendations
            
            Use the provided analyses and past audit context to generate the report.
            """),
            ("user", """
            Original Code Length: {code_len} chars
            
            Security Analysis:
            {security_reports}
            
            Performance Analysis:
            {performance_reports}
            
            Past Audit Context (Memory):
            {past_audits}
            """)
        ])

    def run(self, state: AuditorState) -> AuditorState:
        print("--- Reviewer Agent: Synthesizing Report ---")
        
        security_data = state.get("security_analysis", [])
        performance_data = state.get("performance_analysis", [])
        past_audits = state.get("past_audits", [])
        original_code = state.get("original_code", "")
        
        # Format the inputs for the specific Prompt
        sec_text = "\n".join([f"Snippet {x['snippet_index']}: {x.get('analysis', 'Error: ' + str(x.get('error', 'Unknown')))}" for x in security_data])
        perf_text = "\n".join([f"Snippet {x['snippet_index']}: {x.get('analysis', 'Error: ' + str(x.get('error', 'Unknown')))}" for x in performance_data])
        past_text = "\n".join(past_audits) if past_audits else "No similar past audits found."

        chain = self.prompt | self.llm

        try:
            response = chain.invoke({
                "code_len": len(original_code),
                "security_reports": sec_text,
                "performance_reports": perf_text,
                "past_audits": past_text
            })
            return {"final_report": response.content}
        except Exception as e:
            error_msg = f"Error in Reviewer Agent: {str(e)}"
            print(error_msg)
            return {"final_report": f"# Audit Failed\n\n{error_msg}\n\nSecurity Analysis:\n{sec_text}\n\nPerformance Analysis:\n{perf_text}"}
