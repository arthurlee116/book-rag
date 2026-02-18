import os
import unittest

from fastapi.testclient import TestClient

from backend.app.session_store import SESSIONS, get_or_create_session


class TestLogsEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
        SESSIONS.clear()
        from backend.app.main import app

        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        SESSIONS.clear()

    def test_unknown_session_returns_404_and_does_not_create_session(self) -> None:
        resp = self.client.get("/api/logs/unknown-session-id")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Unknown session", resp.text)
        self.assertEqual(len(SESSIONS), 0)

    def test_empty_upload_does_not_advance_ingest_generation(self) -> None:
        session_id = "empty-upload-session"
        session = get_or_create_session(session_id=session_id, ttl_seconds=1800)
        session.ingest_generation = 7

        resp = self.client.post(
            "/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers={"X-Session-Id": session_id},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("Empty file", resp.text)
        self.assertEqual(session.ingest_generation, 7)


if __name__ == "__main__":
    unittest.main()
