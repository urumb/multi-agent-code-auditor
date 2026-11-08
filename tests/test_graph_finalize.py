import json
import os
import tempfile
import unittest

os.makedirs(r"C:\tmp", exist_ok=True)
os.environ.setdefault(
    "CHROMA_PERSIST_DIRECTORY",
    tempfile.mkdtemp(prefix="auditor_test_chroma_", dir=r"C:\tmp"),
)

from src.graph import finalize_node


class FinalizeNodeTests(unittest.TestCase):
    """Regression test: the fast path (small snippets, Security Agent only)
    used to emit a markdown blob with no findings/risk_score/severity at
    all — meaning the exact "print('hello world')"-scale example called out
    in the project brief would show zero structured results. finalize_node
    must now produce the same structured JSON schema as the full Reviewer
    path.
    """

    def test_produces_structured_report_with_real_findings(self):
        state = {
            "security_analysis": [
                {
                    "snippet_index": 0,
                    "findings": [
                        {
                            "severity": "Critical",
                            "issue": "Hardcoded password",
                            "explanation": "x",
                            "suggested_fix": "y",
                            "before_code": "",
                            "after_code": "",
                            "cwe": "CWE-312",
                            "agent": "security",
                        }
                    ],
                }
            ],
            "performance_analysis": [],
            "quality_analysis": [],
        }

        result = finalize_node(state)
        report = json.loads(result["final_report"])

        self.assertIn("findings", report)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["max_severity"], "Critical")
        self.assertGreater(report["risk_score"], 0)
        self.assertIn("risk_breakdown", report)

    def test_clean_snippet_reports_no_findings_honestly(self):
        state = {"security_analysis": [{"snippet_index": 0, "findings": []}]}
        result = finalize_node(state)
        report = json.loads(result["final_report"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["risk_score"], 0.0)
        self.assertEqual(report["max_severity"], "Low")

    def test_does_not_override_existing_final_report(self):
        state = {"final_report": "already set"}
        result = finalize_node(state)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
