import unittest

from src.agents.reviewer import ReviewerAgent


class ReviewerPromptTemplateTests(unittest.TestCase):
    """Regression test for a bug where the Reviewer Agent's system prompt
    used unescaped `{` `}` around its JSON schema example. LangChain's
    ChatPromptTemplate treats `{x}` as a variable placeholder, so every real
    audit that reached the Reviewer (i.e. any input above the small-snippet
    fast path) failed with "Input to ChatPromptTemplate is missing
    variables" — discarding all real findings from the other three agents
    even though only the narrative synthesis step had failed.

    This doesn't call Ollama; it only exercises local template rendering,
    which is exactly where the bug manifested (the error happens before any
    network call).
    """

    def test_prompt_formats_without_missing_variable_error(self):
        agent = ReviewerAgent()
        # Must not raise — this is the exact call chain.invoke() performs
        # internally before any LLM request is made.
        messages = agent.prompt.format_messages(
            code_len=42,
            security_reports="Snippet 0: no issues",
            performance_reports="Snippet 0: no issues",
            quality_reports="Snippet 0: no issues",
            past_audits="No similar past audits found.",
        )
        self.assertEqual(len(messages), 2)
        system_text = messages[0].content
        # The literal JSON braces from the schema example must survive
        # (i.e. actually be double-braces in source, single after render).
        self.assertIn('"Executive Summary"', system_text)
        self.assertIn('"Findings Summary"', system_text)


if __name__ == "__main__":
    unittest.main()
