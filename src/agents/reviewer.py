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
            ("system", """You are the Lead Code Auditor. Synthesize the findings from the Security, Performance, and Quality teams into a professional JSON report.
            
            Return ONLY valid JSON with this exact shape:
            {
              "Executive Summary": "A high-level overview of the code quality and risks.",
              "Findings Summary": "A short summary of the key findings across all categories."
            }
            
            Do not invent structure.
            """),
            ("user", """
            Original Code Length: {code_len} chars
            
            Security Analysis:
            {security_reports}
            
            Performance Analysis:
            {performance_reports}
            
            Quality Analysis:
            {quality_reports}

            Past Audit Context (Memory):
            {past_audits}
            """)
        ])

    def run(self, state: AuditorState) -> AuditorState:
        print("--- Reviewer Agent: Synthesizing Report ---")
        import json
        from ..findings import _extract_json_object, collect_findings, compute_risk_score
        
        security_data = state.get("security_analysis", [])
        performance_data = state.get("performance_analysis", [])
        quality_data = state.get("quality_analysis", [])
        past_audits = state.get("past_audits", [])
        original_code = state.get("original_code", "")
        
        # Format the inputs for the specific Prompt
        sec_text = "\n".join([f"Snippet {x['snippet_index']}: {x.get('analysis', 'Error: ' + str(x.get('error', 'Unknown')))}" for x in security_data])
        perf_text = "\n".join([f"Snippet {x['snippet_index']}: {x.get('analysis', 'Error: ' + str(x.get('error', 'Unknown')))}" for x in performance_data])
        qual_text = "\n".join([f"Snippet {x['snippet_index']}: {x.get('analysis', 'Error: ' + str(x.get('error', 'Unknown')))}" for x in quality_data])
        past_text = "\n".join(past_audits) if past_audits else "No similar past audits found."

        chain = self.prompt | self.llm

        try:
            response = chain.invoke({
                "code_len": len(original_code),
                "security_reports": sec_text,
                "performance_reports": perf_text,
                "quality_reports": qual_text,
                "past_audits": past_text
            })

            try:
                report_json = _extract_json_object(response.content)
            except json.JSONDecodeError:
                report_json = {
                    "Executive Summary": "Failed to parse LLM output.",
                    "Findings Summary": "Please review the raw output manually."
                }

            # Combine all findings to compute risk score
            all_findings = collect_findings(security_data, performance_data, quality_data)
            risk_info = compute_risk_score(all_findings)

            final_report_dict = {
                "Executive Summary": report_json.get("Executive Summary", ""),
                "Findings Summary": report_json.get("Findings Summary", ""),
                "risk_score": risk_info["risk_score"],
                "findings": all_findings,
                "top_risk_files": [] # Computed higher up if multiple files
            }
            return {"final_report": json.dumps(final_report_dict)}
        except Exception as e:
            error_msg = f"Error in Reviewer Agent: {str(e)}"
            print(error_msg)
            return {"final_report": json.dumps({
                "Executive Summary": "Audit Failed",
                "Findings Summary": error_msg,
                "risk_score": 0.0,
                "top_risk_files": []
            })}
