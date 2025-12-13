import unittest

from backend.app.guardrails import STRICT_NO_MENTION, enforce_strict_rag_answer, extract_citation_numbers


class TestGuardrails(unittest.TestCase):
    def test_extract_citations_ordered_unique(self) -> None:
        text = "A [2] B [1] C [2] D [10]"
        self.assertEqual(extract_citation_numbers(text), [2, 1, 10])

    def test_allows_strict_fallback_without_citations(self) -> None:
        gr = enforce_strict_rag_answer(answer=STRICT_NO_MENTION, context_size=5, require_citations=True)
        self.assertTrue(gr.ok)
        self.assertEqual(gr.answer, STRICT_NO_MENTION)

    def test_rejects_empty_answer(self) -> None:
        gr = enforce_strict_rag_answer(answer="   ", context_size=5, require_citations=True)
        self.assertFalse(gr.ok)
        self.assertEqual(gr.answer, STRICT_NO_MENTION)

    def test_requires_citations_for_non_fallback(self) -> None:
        gr = enforce_strict_rag_answer(answer="Some answer", context_size=5, require_citations=True)
        self.assertFalse(gr.ok)
        self.assertEqual(gr.answer, STRICT_NO_MENTION)

    def test_rejects_out_of_range_citations(self) -> None:
        gr = enforce_strict_rag_answer(answer="Answer [6]", context_size=5, require_citations=True)
        self.assertFalse(gr.ok)
        self.assertEqual(gr.answer, STRICT_NO_MENTION)

    def test_accepts_in_range_citations(self) -> None:
        gr = enforce_strict_rag_answer(answer="Answer [1][2]", context_size=2, require_citations=True)
        self.assertTrue(gr.ok)
        self.assertEqual(gr.answer, "Answer [1][2]")


if __name__ == "__main__":
    unittest.main()

