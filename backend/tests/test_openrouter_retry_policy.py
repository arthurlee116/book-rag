import unittest

import httpx

from backend.app.openrouter_client import OpenRouterError, _is_retryable_exception


class TestOpenRouterRetryPolicy(unittest.TestCase):
    def test_retryable_for_transient_transport_errors(self) -> None:
        self.assertTrue(_is_retryable_exception(httpx.ReadTimeout("timeout")))
        req = httpx.Request("GET", "https://example.com")
        self.assertTrue(_is_retryable_exception(httpx.ConnectError("connect", request=req)))

    def test_retryable_for_transient_status_codes(self) -> None:
        for status in (408, 409, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                self.assertTrue(_is_retryable_exception(OpenRouterError("transient", status_code=status)))

    def test_not_retryable_for_deterministic_4xx(self) -> None:
        for status in (400, 401, 403, 404, 422):
            with self.subTest(status=status):
                self.assertFalse(_is_retryable_exception(OpenRouterError("deterministic", status_code=status)))


if __name__ == "__main__":
    unittest.main()
