import unittest

from backend.app.openrouter_client import OpenRouterClient


class TestOpenRouterJsonExtract(unittest.TestCase):
    def test_extract_json_from_code_fence(self) -> None:
        client = object.__new__(OpenRouterClient)
        raw = "```json\n{\n  \"ranked_ids\": [\"a\", \"b\"]\n}\n```"
        extracted = client._extract_json_text(raw)
        self.assertEqual(extracted, '{\n  "ranked_ids": ["a", "b"]\n}')


if __name__ == "__main__":
    unittest.main()
