# Author: urumb
import logging
from langchain_ollama import ChatOllama
from ..llm import make_llm, invoke_llm, AuditCancelled, REVIEWER_MAX_TOKENS
from langchain_core.prompts import ChatPromptTemplate
from ..config import Config
from ..state import AuditorState

logger = logging.getLogger(__name__)

class ReviewerAgent:
    def __init__(self):
        self._llm_cache: dict[str, ChatOllama] = {}
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Lead Code Auditor. Synthesize the findings from the Security, Performance, and Quality teams into a professional JSON report.

            Return ONLY valid JSON with this exact shape:
            {{
              "Executive Summary": "A high-level overview of the code quality and risks.",
              "Findings Summary": "A short summary of the key findings across all categories."
            }}

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

    def _get_llm(self) -> ChatOllama:
        model = Config.MODEL_NAME
        if model not in self._llm_cache:
            self._llm_cache[model] = make_llm(0, max_tokens=REVIEWER_MAX_TOKENS)
        return self._llm_cache[model]

    @staticmethod
    def _build_summary(findings: list, risk_info: dict, code_len: int) -> dict:
        """Deterministic executive summary derived from the merged findings."""
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.get("severity", "Low")] = counts.get(f.get("severity", "Low"), 0) + 1
        order = ["Critical", "High", "Medium", "Low"]
        breakdown = ", ".join(f"{counts[k]} {k}" for k in order if counts.get(k))
        agents = sorted({str(f.get("agent", "")).title() for f in findings if f.get("agent")})
        if findings:
            top = min(findings, key=lambda f: order.index(f.get("severity", "Low")) if f.get("severity", "Low") in order else 9)
            executive = (
                f"Reviewed {code_len:,} characters of code and merged {len(findings)} finding(s) "
                f"({breakdown}). Highest risk: {top.get('issue', 'n/a')} ({top.get('severity', 'Low')})."
            )
            summary = f"Findings reported by: {', '.join(agents) or 'n/a'}."
        else:
            executive = f"Reviewed {code_len:,} characters of code and found no issues."
            summary = "No findings were reported by any agent."
        return {
            "Executive Summary": executive,
            "Findings Summary": summary,
            "risk_score": risk_info["risk_score"],
            "risk_breakdown": risk_info["risk_breakdown"],
            "max_severity": risk_info["max_severity"],
            "findings": findings,
            "top_risk_files": [],
        }

    def run(self, state: AuditorState) -> AuditorState:
        logger.info("Reviewer Agent: synthesizing report")
        import json
        from ..findings import _extract_json_object, collect_findings, compute_risk_score
        
        security_data = state.get("security_analysis", [])
        performance_data = state.get("performance_analysis", [])
        quality_data = state.get("quality_analysis", [])
        past_audits = state.get("past_audits", [])
        original_code = state.get("original_code", "")
        
        # Format the inputs for the specific Prompt
        def _compact(items: list) -> str:
            # One short line per finding instead of the agents' full raw
            # output: far fewer prompt tokens to process on a CPU, and the
            # reviewer only needs to write a two-sentence summary.
            lines = []
            for x in items:
                if x.get("error"):
                    lines.append(f"(analysis error: {str(x['error'])[:80]})")
                    continue
                for f in x.get("findings", []):
                    lines.append(f"- [{f.get('severity', 'Low')}] {str(f.get('issue', ''))[:100]}")
            return "\n".join(lines) if lines else "No issues reported."

        sec_text = _compact(security_data)
        perf_text = _compact(performance_data)
        qual_text = _compact(quality_data)
        past_text = "\n".join(past_audits)[:400] if past_audits else "No similar past audits found."

        # Computed up front (doesn't depend on the LLM call) so a synthesis
        # failure below never discards the real findings the other three
        # agents already produced.
        all_findings = collect_findings(security_data, performance_data, quality_data)
        risk_info = compute_risk_score(all_findings)

        if not Config.REVIEWER_USE_LLM:
            return {"final_report": json.dumps(self._build_summary(all_findings, risk_info, len(original_code)))}

        chain = self.prompt | self._get_llm()

        try:
            response = invoke_llm(chain, {
                "code_len": len(original_code),
                "security_reports": sec_text,
                "performance_reports": perf_text,
                "quality_reports": qual_text,
                "past_audits": past_text
            }, state.get("cancel_event"))

            try:
                report_json = _extract_json_object(response.content)
            except json.JSONDecodeError:
                report_json = {
                    "Executive Summary": "Failed to parse the reviewer's synthesis output.",
                    "Findings Summary": "The findings below are still accurate — only the narrative summary failed to parse.",
                }

            final_report_dict = {
                "Executive Summary": report_json.get("Executive Summary", ""),
                "Findings Summary": report_json.get("Findings Summary", ""),
                "risk_score": risk_info["risk_score"],
                "risk_breakdown": risk_info["risk_breakdown"],
                "max_severity": risk_info["max_severity"],
                "findings": all_findings,
                "top_risk_files": [] # Computed higher up if multiple files
            }
            return {"final_report": json.dumps(final_report_dict)}
        except AuditCancelled:
            raise
        except Exception as e:
            error_msg = f"Error in Reviewer Agent: {str(e)}"
            logger.error(error_msg)
            return {"final_report": json.dumps({
                "Executive Summary": "The Reviewer Agent's narrative synthesis failed, but the findings below were still detected.",
                "Findings Summary": error_msg,
                "risk_score": risk_info["risk_score"],
                "risk_breakdown": risk_info["risk_breakdown"],
                "max_severity": risk_info["max_severity"],
                "findings": all_findings,
                "top_risk_files": []
            })}
