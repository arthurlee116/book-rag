import unittest

from backend.app.config import Settings
from backend.app.openrouter_client import ChatMessage, OpenRouterClient


class _FakeResponse:
    status_code = 200

    def __init__(self, payload) -> None:
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload) -> None:
        self.last_json = None
        self._payload = payload

    async def post(self, _path: str, json=None):
        self.last_json = json
        return _FakeResponse(self._payload)


class TestOpenRouterChatRequest(unittest.IsolatedAsyncioTestCase):
    async def test_chat_completion_requests_bounded_reasoning_tokens(self) -> None:
        client = OpenRouterClient(Settings(openrouter_api_key="test-key"))
        fake_client = _FakeAsyncClient(
            {
                "choices": [
                    {
                        "message": {
                            "content": "OK",
                            "reasoning": "Let me think...",
                        }
                    }
                ]
            }
        )
        real_client = client._client
        client._client = fake_client
        try:
            content = await client.chat_completion(
                model="qwen/qwen3.5-35b-a3b",
                messages=[ChatMessage(role="user", content="Reply with OK.")],
            )
        finally:
            client._client = real_client
            if real_client is not None:
                await real_client.aclose()

        self.assertEqual(content, "OK")
        self.assertEqual(fake_client.last_json["reasoning"], {"max_tokens": 64})

    async def test_chat_completion_extracts_text_from_content_parts(self) -> None:
        client = OpenRouterClient(Settings(openrouter_api_key="test-key"))
        fake_client = _FakeAsyncClient(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "output_text", "text": "Ponyboy is the narrator [1]."},
                            ],
                            "reasoning_details": [
                                {"type": "reasoning.text", "text": "Need to use the provided context only."}
                            ],
                        }
                    }
                ]
            }
        )
        real_client = client._client
        client._client = fake_client
        try:
            content = await client.chat_completion(
                model="qwen/qwen3.5-35b-a3b",
                messages=[ChatMessage(role="user", content="Who is the narrator?")],
            )
        finally:
            client._client = real_client
            if real_client is not None:
                await real_client.aclose()

        self.assertEqual(content, "Ponyboy is the narrator [1].")


if __name__ == "__main__":
    unittest.main()
