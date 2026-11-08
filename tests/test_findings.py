import unittest

from src.findings import (
    _extract_json_object,
    collect_findings,
    compute_risk_score,
    normalize_findings,
)


class ExtractJsonObjectTests(unittest.TestCase):
    """Regression tests for the JSON-extraction bug: local models (llama3.2)
    routinely wrap illustrative code examples in their own ``` fences before
    the actual JSON answer. The extractor must find the real JSON, not the
    first fenced block it sees."""

    def test_plain_json(self):
        self.assertEqual(_extract_json_object('{"findings": []}'), {"findings": []})

    def test_single_json_fence(self):
        text = '```json\n{"findings": []}\n```'
        self.assertEqual(_extract_json_object(text), {"findings": []})

    def test_prose_then_code_fence_then_json_fence(self):
        text = (
            "Here is my analysis.\n\n"
            "```python\nimport os\npassword = 'x'\n```\n\n"
            "```json\n"
            '{"findings": [{"severity": "Critical", "issue": "Hardcoded secret"}]}\n'
            "```"
        )
        result = _extract_json_object(text)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["issue"], "Hardcoded secret")

    def test_multiple_code_fences_no_json_tag(self):
        text = (
            "```python\nx = 1\n```\n\n"
            'Final answer: ```\n{"findings": [{"severity": "Low", "issue": "ok"}]}\n```'
        )
        result = _extract_json_object(text)
        self.assertEqual(result["findings"][0]["issue"], "ok")

    def test_no_json_raises(self):
        with self.assertRaises(Exception):
            _extract_json_object("no json here at all")


class NormalizeFindingsTests(unittest.TestCase):
    def test_realistic_llm_output_with_leading_code_fence(self):
        raw = (
            "**Security Analysis**\n\n"
            "### Hardcoded Secret\n\n"
            "```python\npassword = 'x'\n```\n\n"
            "```json\n"
            '{"findings": [{"severity": "Critical", "issue": "Hardcoded Secret", '
            '"explanation": "bad", "suggested_fix": "use env vars", '
            '"before_code": "", "after_code": "", "cwe": "CWE-312"}]}\n'
            "```"
        )
        findings = normalize_findings(raw, "security", raw)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "Critical")
        self.assertEqual(findings[0]["issue"], "Hardcoded Secret")
        self.assertEqual(findings[0]["agent"], "security")

    def test_malformed_output_degrades_to_single_low_finding(self):
        findings = normalize_findings("not json and no fences", "security", "code")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "Low")

    def test_empty_findings_list(self):
        self.assertEqual(normalize_findings('{"findings": []}', "security"), [])


class RiskScoreTests(unittest.TestCase):
    def test_collect_and_score(self):
        security_data = [
            {
                "snippet_index": 0,
                "findings": [
                    {"severity": "Critical", "agent": "security"},
                    {"severity": "Low", "agent": "security"},
                ],
            }
        ]
        performance_data = [{"snippet_index": 0, "findings": [{"severity": "High", "agent": "performance"}]}]

        all_findings = collect_findings(security_data, performance_data, [])
        self.assertEqual(len(all_findings), 3)

        risk = compute_risk_score(all_findings)
        self.assertEqual(risk["max_severity"], "Critical")
        self.assertGreater(risk["risk_score"], 0)
        self.assertIn("security", risk["risk_breakdown"])
        self.assertIn("performance", risk["risk_breakdown"])

    def test_no_findings_is_zero_risk(self):
        risk = compute_risk_score([])
        self.assertEqual(risk["risk_score"], 0.0)
        self.assertEqual(risk["max_severity"], "Low")


if __name__ == "__main__":
    unittest.main()
