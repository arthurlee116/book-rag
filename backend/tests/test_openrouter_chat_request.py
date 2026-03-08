import unittest

from backend.app.config import Settings
from backend.app.openrouter_client import ChatMessage, OpenRouterClient


class _FakeResponse:
    status_code = 200

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": "OK",
                    }
                }
            ]
        }


class _FakeAsyncClient:
    def __init__(self) -> None:
        self.last_json = None

    async def post(self, _path: str, json=None):
        self.last_json = json
        return _FakeResponse()


class TestOpenRouterChatRequest(unittest.IsolatedAsyncioTestCase):
    async def test_chat_completion_disables_reasoning_by_default(self) -> None:
        client = OpenRouterClient(Settings(openrouter_api_key="test-key"))
        fake_client = _FakeAsyncClient()
        real_client = client._client
        client._client = fake_client
        try:
            content = await client.chat_completion(
                model="qwen/qwen3.5-35b-a3b",
                messages=[ChatMessage(role="user", content="Reply with OK.")],
            )
        finally:
            client._client = real_client
            await real_client.aclose()

        self.assertEqual(content, "OK")
        self.assertEqual(
            fake_client.last_json["reasoning"],
            {"effort": "none", "exclude": True},
        )


if __name__ == "__main__":
    unittest.main()
